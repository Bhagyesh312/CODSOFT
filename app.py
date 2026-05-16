import os
import re
import random
import string
import logging
from datetime import datetime, timezone, timedelta

from flask import (Flask, render_template, redirect, url_for, request,
                   flash, jsonify, abort)
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

from config import Config, MIN_TIMER_SECONDS, MAX_TIMER_SECONDS, MIN_BONUS_POINTS, \
    MAX_BONUS_POINTS, MAX_PENALTY, MIN_PENALTY, MIN_PASSWORD_LENGTH, \
    MAX_TITLE_LENGTH, MAX_DESC_LENGTH
from models import db, User, Quiz, Question, Option, Attempt, AttemptAnswer, UserBadge, BADGE_DEFINITIONS

logger = logging.getLogger('thinksprint')

app = Flask(__name__)
app.config.from_object(Config)

# ── Groq AI setup ─────────────────────────────────────────────────────────────
def _call_groq(prompt: str) -> str:
    """Call Groq API via official SDK and return text, or empty string on failure."""
    api_key = os.environ.get('GROQ_API_KEY', '')
    if not api_key:
        return ''
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        chat = client.chat.completions.create(
            model='llama-3.1-8b-instant',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=150,
            temperature=0.3,
        )
        return chat.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f'Groq API call failed: {e}')
        return ''

# ── Image upload config ────────────────────────────────────────────────────────
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024   # 5 MB max per image

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_question_image(file):
    """Save uploaded image, return stored filename or None."""
    if not file or file.filename == '':
        return None
    if not allowed_file(file.filename):
        return None
    try:
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_name = f"{random.randint(100000, 999999)}_{secure_filename(file.filename)}"
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
        return unique_name
    except Exception as e:
        logger.error(f'Image upload failed: {e}')
        return None


def generate_join_code():
    """Generate a unique ABC123-style 6-character join code."""
    while True:
        letters = ''.join(random.choices(string.ascii_uppercase, k=3))
        digits = ''.join(random.choices(string.digits, k=3))
        code = letters + digits
        if not Quiz.query.filter_by(join_code=code).first():
            return code


def calculate_bonus(quiz):
    """Assign bonus to highest scorer(s) with least time. Requires ≥2 participants."""
    if not quiz.bonus_enabled:
        return

    submitted = Attempt.query.filter_by(quiz_id=quiz.id, is_submitted=True).all()
    if len(submitted) < 2:
        return

    for a in submitted:
        a.bonus_points = 0

    highest_net = max(a.net_score for a in submitted)
    top_scorers = [a for a in submitted if a.net_score == highest_net]
    min_time = min(a.time_taken for a in top_scorers)
    winners = [a for a in top_scorers if a.time_taken == min_time]

    for w in winners:
        w.bonus_points = quiz.bonus_points

    db.session.commit()


def _award_badge(user, badge_key):
    """Award a badge to a user if they don't already have it."""
    if not user.has_badge(badge_key):
        db.session.add(UserBadge(user_id=user.id, badge_key=badge_key))


def evaluate_badges(attempt):
    """Check all badge conditions after a quiz submission and award as needed."""
    user = attempt.user
    quiz = attempt.quiz

    # ── Perfect Score ──────────────────────────────────────────────────────────
    if attempt.total > 0 and attempt.score == attempt.total:
        _award_badge(user, 'perfect_score')

    # ── Speed Demon ────────────────────────────────────────────────────────────
    # User is in the fastest 25% of all submitted attempts for this quiz
    all_submitted = Attempt.query.filter_by(quiz_id=quiz.id, is_submitted=True).all()
    if len(all_submitted) >= 2:
        times = sorted(a.time_taken for a in all_submitted)
        cutoff_index = max(0, int(len(times) * 0.25) - 1)
        cutoff_time = times[cutoff_index]
        if attempt.time_taken <= cutoff_time:
            _award_badge(user, 'speed_demon')

    # ── Quiz Veteran ───────────────────────────────────────────────────────────
    total_attempts = Attempt.query.filter_by(user_id=user.id, is_submitted=True).count()
    if total_attempts >= 10:
        _award_badge(user, 'quiz_veteran')

    # ── Streak Master ──────────────────────────────────────────────────────────
    if (user.current_streak or 0) >= 3:
        _award_badge(user, 'streak_master')

    # ── Top Scholar ────────────────────────────────────────────────────────────
    # Check if this user is rank #1 on this quiz leaderboard
    sorted_attempts = sorted(
        all_submitted,
        key=lambda a: (-(a.net_score + a.bonus_points), a.time_taken)
    )
    if sorted_attempts and sorted_attempts[0].user_id == user.id:
        _award_badge(user, 'top_scholar')

    db.session.commit()


def parse_quiz_settings(form):
    """Extract and validate common quiz settings from a form."""
    title = form.get('title', '').strip()[:MAX_TITLE_LENGTH]
    description = form.get('description', '').strip()[:MAX_DESC_LENGTH]
    # join_window_minutes may be absent if public quiz hides the field — default to 10
    try:
        join_window = int(form.get('join_window_minutes', 10) or 10)
    except (ValueError, TypeError):
        join_window = 10
    return {
        'title': title,
        'description': description,
        'timer_per_question': int(form.get('timer_per_question', 30)),
        'join_window_minutes': join_window,
        'allow_multiple_attempts': form.get('allow_multiple_attempts') == 'on',
        'bonus_enabled': form.get('bonus_enabled') == 'on',
        'bonus_points': int(form.get('bonus_points', 2)),
        'shuffle_questions': form.get('shuffle_questions') == 'on',
        'negative_marking': form.get('negative_marking') == 'on',
        'negative_penalty': float(form.get('negative_penalty', 0.5)),
        'is_public': form.get('is_public') == 'on',
    }


# ─────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not name or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('auth/register.html')
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')
        if len(password) < MIN_PASSWORD_LENGTH:
            flash(f'Password must be at least {MIN_PASSWORD_LENGTH} characters.', 'danger')
            return render_template('auth/register.html')
        if not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
            flash('Password must contain at least one letter and one number.', 'danger')
            return render_template('auth/register.html')
        if len(name) > 100:
            flash('Name must be 100 characters or fewer.', 'danger')
            return render_template('auth/register.html')
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('auth/register.html')

        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        logger.info(f'New user registered: {email}')
        flash(f'Welcome to ThinkSprint, {name}!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('auth/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            # Prevent open redirect — only allow relative paths
            if next_page and (next_page.startswith('http') or next_page.startswith('//')):
                next_page = None
            logger.info(f'User logged in: {email}')
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(next_page or url_for('dashboard'))
        logger.warning(f'Failed login attempt for: {email}')
        flash('Invalid email or password.', 'danger')

    return render_template('auth/login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


# ─────────────────────────────────────────────
# CREATOR ROUTES
# ─────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    quizzes = Quiz.query.filter_by(creator_id=current_user.id).order_by(Quiz.created_at.desc()).all()
    return render_template('creator/dashboard.html', quizzes=quizzes)


@app.route('/quiz/create', methods=['GET', 'POST'])
@login_required
def create_quiz():
    if request.method == 'POST':
        s = parse_quiz_settings(request.form)

        if not s['title']:
            flash('Quiz title is required.', 'danger')
            return render_template('creator/create_quiz.html')
        if s['timer_per_question'] < MIN_TIMER_SECONDS or s['timer_per_question'] > MAX_TIMER_SECONDS:
            flash(f'Timer must be between {MIN_TIMER_SECONDS} and {MAX_TIMER_SECONDS} seconds.', 'danger')
            return render_template('creator/create_quiz.html')
        if s['bonus_enabled'] and (s['bonus_points'] < MIN_BONUS_POINTS or s['bonus_points'] > MAX_BONUS_POINTS):
            flash(f'Bonus points must be between {MIN_BONUS_POINTS} and {MAX_BONUS_POINTS}.', 'danger')
            return render_template('creator/create_quiz.html')
        if s['negative_marking'] and (s['negative_penalty'] < MIN_PENALTY or s['negative_penalty'] > MAX_PENALTY):
            flash(f'Penalty must be between {MIN_PENALTY} and {MAX_PENALTY}.', 'danger')
            return render_template('creator/create_quiz.html')

        question_texts = request.form.getlist('question_text[]')
        if not question_texts or all(q.strip() == '' for q in question_texts):
            flash('Add at least one question.', 'danger')
            return render_template('creator/create_quiz.html')

        quiz = Quiz(
            title=s['title'],
            description=s['description'],
            timer_per_question=s['timer_per_question'],
            join_window_minutes=s['join_window_minutes'],
            allow_multiple_attempts=s['allow_multiple_attempts'],
            bonus_enabled=s['bonus_enabled'],
            bonus_points=s['bonus_points'] if s['bonus_enabled'] else 0,
            shuffle_questions=s['shuffle_questions'],
            negative_marking=s['negative_marking'],
            negative_penalty=s['negative_penalty'] if s['negative_marking'] else 0.0,
            is_public=s['is_public'],
            creator_id=current_user.id
        )
        # Public quizzes are always active — no join code or window needed
        if s['is_public']:
            quiz.is_active = True
            quiz.join_code = None
            quiz.code_expires_at = None
            quiz.allow_multiple_attempts = True  # force on for public quizzes
        db.session.add(quiz)
        db.session.flush()

        image_files = request.files.getlist('question_image[]')

        for idx, q_text in enumerate(question_texts):
            q_text = q_text.strip()
            if not q_text:
                continue

            # Handle optional image upload for this question
            image_filename = None
            if idx < len(image_files):
                image_filename = save_question_image(image_files[idx])

            explanations = request.form.getlist('explanation[]')
            explanation_text = explanations[idx].strip() if idx < len(explanations) else ''

            question = Question(
                quiz_id=quiz.id,
                question_text=q_text,
                image_path=image_filename,
                order_index=idx,
                explanation=explanation_text or None
            )
            db.session.add(question)
            db.session.flush()

            option_texts = request.form.getlist(f'option_text_{idx}[]')
            correct_index = request.form.get(f'correct_option_{idx}', '0')

            valid_options = [o.strip() for o in option_texts if o.strip()]
            if len(valid_options) < 2:
                db.session.rollback()
                flash(f'Question {idx + 1} needs at least 2 options.', 'danger')
                return render_template('creator/create_quiz.html')

            has_correct = False
            for opt_idx, opt_text in enumerate(option_texts):
                opt_text = opt_text.strip()
                if not opt_text:
                    continue
                is_correct = (str(opt_idx) == str(correct_index))
                if is_correct:
                    has_correct = True
                db.session.add(Option(
                    question_id=question.id,
                    option_text=opt_text,
                    is_correct=is_correct
                ))

            if not has_correct:
                db.session.rollback()
                flash(f'Question {idx + 1} must have a correct answer selected.', 'danger')
                return render_template('creator/create_quiz.html')

        db.session.commit()
        logger.info(f'Quiz created: id={quiz.id} title="{quiz.title}" by user={current_user.id}')
        flash('Quiz created successfully! Start it when ready.', 'success')
        return redirect(url_for('manage_quiz', quiz_id=quiz.id))

    return render_template('creator/create_quiz.html')


@app.route('/quiz/<int:quiz_id>/manage')
@login_required
def manage_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.creator_id != current_user.id:
        abort(403)

    raw_attempts = Attempt.query.filter_by(quiz_id=quiz_id, is_submitted=True).all()
    attempts = sorted(raw_attempts, key=lambda a: (-(a.net_score + a.bonus_points), a.time_taken))

    # Live participant count (joined but not necessarily submitted)
    participant_count = Attempt.query.filter_by(quiz_id=quiz_id).count()

    return render_template('creator/manage_quiz.html',
                           quiz=quiz,
                           attempts=attempts,
                           participant_count=participant_count)


@app.route('/quiz/<int:quiz_id>/participant-count')
@login_required
def participant_count(quiz_id):
    """JSON endpoint polled by manage page for live count."""
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.creator_id != current_user.id:
        abort(403)
    total = Attempt.query.filter_by(quiz_id=quiz_id).count()
    submitted = Attempt.query.filter_by(quiz_id=quiz_id, is_submitted=True).count()
    return jsonify({'total': total, 'submitted': submitted})


@app.route('/quiz/<int:quiz_id>/start', methods=['POST'])
@login_required
def start_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.creator_id != current_user.id:
        abort(403)
    if quiz.total_questions == 0:
        flash('Add at least one question before starting.', 'danger')
        return redirect(url_for('manage_quiz', quiz_id=quiz_id))

    quiz.join_code = generate_join_code()
    quiz.is_active = True
    quiz.code_expires_at = datetime.now(timezone.utc) + timedelta(minutes=quiz.join_window_minutes)
    db.session.commit()

    flash(f'Quiz started! Join code: {quiz.join_code} (valid for {quiz.join_window_minutes} minutes)', 'success')
    return redirect(url_for('manage_quiz', quiz_id=quiz_id))


@app.route('/quiz/<int:quiz_id>/regenerate-code', methods=['POST'])
@login_required
def regenerate_code(quiz_id):
    """Generate a fresh join code and reset the expiry window."""
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.creator_id != current_user.id:
        abort(403)
    if not quiz.is_active:
        flash('Quiz must be active to regenerate a code.', 'warning')
        return redirect(url_for('manage_quiz', quiz_id=quiz_id))

    quiz.join_code = generate_join_code()
    quiz.code_expires_at = datetime.now(timezone.utc) + timedelta(minutes=quiz.join_window_minutes)
    db.session.commit()
    flash(f'New join code generated: {quiz.join_code} (valid for {quiz.join_window_minutes} minutes)', 'success')
    return redirect(url_for('manage_quiz', quiz_id=quiz_id))


@app.route('/quiz/<int:quiz_id>/end', methods=['POST'])
@login_required
def end_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.creator_id != current_user.id:
        abort(403)
    quiz.is_active = False
    db.session.commit()
    calculate_bonus(quiz)
    flash('Quiz ended. Bonus points have been calculated.', 'success')
    return redirect(url_for('manage_quiz', quiz_id=quiz_id))


@app.route('/quiz/<int:quiz_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.creator_id != current_user.id:
        abort(403)
    if quiz.has_attempts:
        flash('This quiz cannot be edited because it already has attempts.', 'warning')
        return redirect(url_for('manage_quiz', quiz_id=quiz_id))

    if request.method == 'POST':
        s = parse_quiz_settings(request.form)
        quiz.title = s['title']
        quiz.description = s['description']
        quiz.timer_per_question = s['timer_per_question']
        quiz.join_window_minutes = s['join_window_minutes']
        quiz.allow_multiple_attempts = s['allow_multiple_attempts']
        quiz.bonus_enabled = s['bonus_enabled']
        quiz.bonus_points = s['bonus_points'] if s['bonus_enabled'] else 0
        quiz.shuffle_questions = s['shuffle_questions']
        quiz.negative_marking = s['negative_marking']
        quiz.negative_penalty = s['negative_penalty'] if s['negative_marking'] else 0.0
        quiz.is_public = s['is_public']
        # Public quizzes: force active, clear join code, force multiple attempts
        if s['is_public']:
            quiz.is_active = True
            quiz.join_code = None
            quiz.code_expires_at = None
            quiz.allow_multiple_attempts = True
        else:
            # Switching back to private: deactivate so creator must manually start
            quiz.is_active = False
        db.session.commit()
        flash('Quiz updated.', 'success')
        return redirect(url_for('manage_quiz', quiz_id=quiz_id))

    return render_template('creator/edit_quiz.html', quiz=quiz)


@app.route('/quiz/<int:quiz_id>/delete', methods=['POST'])
@login_required
def delete_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.creator_id != current_user.id:
        abort(403)
    db.session.delete(quiz)
    db.session.commit()
    flash('Quiz deleted.', 'info')
    return redirect(url_for('dashboard'))


# ─────────────────────────────────────────────
# PARTICIPANT ROUTES
# ─────────────────────────────────────────────

@app.route('/join', methods=['GET', 'POST'])
@login_required
def join_quiz():
    if request.method == 'POST':
        code = request.form.get('join_code', '').strip().upper()
        quiz = Quiz.query.filter_by(join_code=code).first()

        if not quiz:
            flash('Invalid join code.', 'danger')
            return render_template('participant/join.html')
        if not quiz.is_active:
            flash('This quiz is not active.', 'danger')
            return render_template('participant/join.html')
        if not quiz.join_code_valid:
            flash('Join code has expired. No new participants can join.', 'danger')
            return render_template('participant/join.html')
        if quiz.creator_id == current_user.id:
            flash('You cannot take your own quiz.', 'warning')
            return render_template('participant/join.html')

        existing = Attempt.query.filter_by(quiz_id=quiz.id, user_id=current_user.id).first()
        if existing:
            if existing.is_submitted and not quiz.allow_multiple_attempts:
                flash('You have already completed this quiz.', 'warning')
                return redirect(url_for('quiz_result', attempt_id=existing.id))
            elif not existing.is_submitted:
                return redirect(url_for('take_quiz', attempt_id=existing.id))

        attempt = Attempt(
            quiz_id=quiz.id,
            user_id=current_user.id,
            total=quiz.total_questions,
            is_submitted=False
        )
        db.session.add(attempt)
        db.session.commit()
        return redirect(url_for('take_quiz', attempt_id=attempt.id))

    return render_template('participant/join.html')


@app.route('/quiz/take/<int:attempt_id>')
@login_required
def take_quiz(attempt_id):
    attempt = Attempt.query.get_or_404(attempt_id)
    if attempt.user_id != current_user.id:
        abort(403)
    if attempt.is_submitted:
        return redirect(url_for('quiz_result', attempt_id=attempt_id))

    quiz = attempt.quiz
    participant_count = Attempt.query.filter_by(quiz_id=quiz.id).count()

    questions = list(quiz.questions)
    if quiz.shuffle_questions and participant_count >= 2:
        random.shuffle(questions)
    else:
        questions.sort(key=lambda q: q.order_index)

    for q in questions:
        random.shuffle(q.options)

    return render_template('participant/take_quiz.html',
                           quiz=quiz,
                           attempt=attempt,
                           questions=questions)


@app.route('/quiz/submit/<int:attempt_id>', methods=['POST'])
@login_required
def submit_quiz(attempt_id):
    attempt = Attempt.query.get_or_404(attempt_id)
    if attempt.user_id != current_user.id:
        abort(403)
    if attempt.is_submitted:
        return jsonify({'success': True, 'redirect': url_for('quiz_result', attempt_id=attempt.id)})

    quiz = attempt.quiz
    data = request.get_json()
    if not data:
        abort(400)

    answers = data.get('answers', [])
    total_time = data.get('total_time', 0)

    # ── Server-side time cap: total time cannot exceed timer × questions + 30s buffer ──
    max_allowed_time = (quiz.timer_per_question * quiz.total_questions) + 30
    total_time = min(int(total_time), max_allowed_time)

    score = 0
    penalty = 0.0

    for ans in answers:
        question_id = ans.get('question_id')
        selected_option_id = ans.get('selected_option_id')
        time_taken_sec = ans.get('time_taken_seconds', 0)

        question = Question.query.get(question_id)
        # Guard: question must belong to this quiz
        if not question or question.quiz_id != quiz.id:
            continue

        is_correct = False
        if selected_option_id:
            option = Option.query.get(selected_option_id)
            # Guard: option must belong to this question
            if option and option.question_id == question_id:
                if option.is_correct:
                    is_correct = True
                    score += 1
                elif quiz.negative_marking:
                    penalty += quiz.negative_penalty

        db.session.add(AttemptAnswer(
            attempt_id=attempt.id,
            question_id=question_id,
            selected_option_id=selected_option_id,
            is_correct=is_correct,
            time_taken_seconds=time_taken_sec
        ))

    attempt.score = score
    attempt.penalty = round(penalty, 2)
    attempt.total = quiz.total_questions
    attempt.time_taken = total_time
    attempt.is_submitted = True
    attempt.taken_at = datetime.now(timezone.utc)
    db.session.commit()

    logger.info(
        f'Quiz submitted: attempt={attempt.id} user={current_user.id} '
        f'quiz={quiz.id} score={score}/{quiz.total_questions} time={total_time}s'
    )

    if not quiz.is_active:
        calculate_bonus(quiz)

    # ── Streak & badge evaluation ──────────────────────────────────────────────
    user = attempt.user
    user.update_streak()
    db.session.commit()
    evaluate_badges(attempt)

    return jsonify({'success': True, 'redirect': url_for('quiz_result', attempt_id=attempt.id)})


@app.route('/quiz/result/<int:attempt_id>')
@login_required
def quiz_result(attempt_id):
    attempt = Attempt.query.get_or_404(attempt_id)
    if attempt.user_id != current_user.id and attempt.quiz.creator_id != current_user.id:
        abort(403)
    if not attempt.is_submitted:
        return redirect(url_for('take_quiz', attempt_id=attempt_id))

    quiz = attempt.quiz
    review = []
    for ans in attempt.answers:
        question = ans.question
        correct_option = next((o for o in question.options if o.is_correct), None)
        review.append({
            'question': question,
            'selected_option': ans.selected_option,
            'correct_option': correct_option,
            'is_correct': ans.is_correct,
            'time_taken_seconds': ans.time_taken_seconds
        })

    leaderboard = _get_leaderboard(quiz.id, current_user.id)
    return render_template('participant/result.html',
                           attempt=attempt,
                           quiz=quiz,
                           review=review,
                           leaderboard=leaderboard)


@app.route('/quiz/<int:quiz_id>/leaderboard')
@login_required
def leaderboard(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    is_creator = quiz.creator_id == current_user.id
    user_attempt = Attempt.query.filter_by(
        quiz_id=quiz_id, user_id=current_user.id, is_submitted=True
    ).first()

    if not is_creator and not user_attempt:
        flash('You must complete the quiz to view the leaderboard.', 'warning')
        return redirect(url_for('join_quiz'))

    leaderboard_data = _get_leaderboard(quiz_id, current_user.id)
    return render_template('participant/leaderboard.html',
                           quiz=quiz,
                           leaderboard=leaderboard_data,
                           is_creator=is_creator)


def _get_leaderboard(quiz_id, current_user_id):
    """Build leaderboard. When multiple attempts allowed, show only best per user."""
    attempts = Attempt.query.filter_by(quiz_id=quiz_id, is_submitted=True).all()

    # Deduplicate: keep best attempt per user (highest final_score, then lowest time)
    best_by_user = {}
    for a in attempts:
        uid = a.user_id
        if uid not in best_by_user:
            best_by_user[uid] = a
        else:
            existing = best_by_user[uid]
            if (a.final_score, -a.time_taken) > (existing.final_score, -existing.time_taken):
                best_by_user[uid] = a

    board = []
    for idx, a in enumerate(
        sorted(best_by_user.values(), key=lambda x: (-(x.net_score + x.bonus_points), x.time_taken))
    ):
        board.append({
            'rank': idx + 1,
            'name': a.user.name if a.user else 'Unknown',
            'score': a.score,
            'penalty': a.penalty,
            'net_score': a.net_score,
            'bonus': a.bonus_points,
            'final_score': a.final_score,
            'total': a.total,
            'time_taken': a.time_taken,
            'is_current_user': a.user_id == current_user_id,
        })
    return board


# ─────────────────────────────────────────────
# PROFILE & HISTORY ROUTES
# ─────────────────────────────────────────────

@app.route('/profile')
@login_required
def profile():
    quizzes_created = Quiz.query.filter_by(creator_id=current_user.id).count()
    attempts_taken = Attempt.query.filter_by(user_id=current_user.id, is_submitted=True).count()
    recent_attempts = (
        Attempt.query
        .filter_by(user_id=current_user.id, is_submitted=True)
        .order_by(Attempt.taken_at.desc())
        .limit(5).all()
    )

    # Build badge status list: all defined badges with earned/locked state
    earned_keys = {b.badge_key: b.earned_at for b in current_user.badges}
    badge_list = []
    for key, defn in BADGE_DEFINITIONS.items():
        badge_list.append({
            'key': key,
            'name': defn['name'],
            'description': defn['description'],
            'color': defn['color'],
            'earned': key in earned_keys,
            'earned_at': earned_keys.get(key),
        })

    return render_template('profile.html',
                           quizzes_created=quizzes_created,
                           attempts_taken=attempts_taken,
                           recent_attempts=recent_attempts,
                           badge_list=badge_list)


@app.route('/my-attempts')
@login_required
def my_attempts():
    attempts = (
        Attempt.query
        .filter_by(user_id=current_user.id, is_submitted=True)
        .order_by(Attempt.taken_at.desc()).all()
    )
    return render_template('participant/my_attempts.html', attempts=attempts)


@app.route('/quiz/<int:quiz_id>/preview')
@login_required
def preview_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.creator_id != current_user.id:
        abort(403)
    return render_template('creator/preview_quiz.html', quiz=quiz)


@app.route('/quiz/<int:quiz_id>/analytics')
@login_required
def quiz_analytics(quiz_id):
    """Per-question analytics for the quiz creator."""
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.creator_id != current_user.id:
        abort(403)

    total_submitted = Attempt.query.filter_by(quiz_id=quiz_id, is_submitted=True).count()

    analytics = []
    for q in sorted(quiz.questions, key=lambda x: x.order_index):
        answers = AttemptAnswer.query.filter_by(question_id=q.id).all()
        # Only count answers from submitted attempts
        submitted_answers = [
            a for a in answers
            if Attempt.query.get(a.attempt_id) and Attempt.query.get(a.attempt_id).is_submitted
        ]
        total_ans   = len(submitted_answers)
        correct     = sum(1 for a in submitted_answers if a.is_correct)
        skipped     = sum(1 for a in submitted_answers if a.selected_option_id is None)
        wrong       = total_ans - correct - skipped
        avg_time    = round(
            sum(a.time_taken_seconds for a in submitted_answers) / total_ans, 1
        ) if total_ans else 0
        pct_correct = round((correct / total_ans) * 100) if total_ans else 0

        # Most common wrong answer
        wrong_counts = {}
        for a in submitted_answers:
            if not a.is_correct and a.selected_option_id:
                opt = Option.query.get(a.selected_option_id)
                if opt:
                    wrong_counts[opt.option_text] = wrong_counts.get(opt.option_text, 0) + 1
        top_wrong = max(wrong_counts, key=wrong_counts.get) if wrong_counts else None

        analytics.append({
            'question': q,
            'total':       total_ans,
            'correct':     correct,
            'wrong':       wrong,
            'skipped':     skipped,
            'avg_time':    avg_time,
            'pct_correct': pct_correct,
            'top_wrong':   top_wrong,
        })

    return render_template('creator/analytics.html',
                           quiz=quiz,
                           analytics=analytics,
                           total_submitted=total_submitted)


# ─────────────────────────────────────────────
# PUBLIC QUIZ LISTING
# ─────────────────────────────────────────────

@app.route('/quizzes')
@login_required
def quiz_listing():
    """Browse all public quizzes that are currently active."""
    search = request.args.get('q', '').strip()

    query = Quiz.query.filter_by(is_public=True, is_active=True)
    if search:
        query = query.filter(Quiz.title.ilike(f'%{search}%'))

    # Exclude quizzes created by the current user
    query = query.filter(Quiz.creator_id != current_user.id)

    quizzes = query.order_by(Quiz.created_at.desc()).all()

    # Annotate each quiz with whether the user already attempted it
    attempted_ids = {
        a.quiz_id for a in Attempt.query.filter_by(
            user_id=current_user.id, is_submitted=True
        ).all()
    }

    return render_template('participant/quiz_listing.html',
                           quizzes=quizzes,
                           attempted_ids=attempted_ids,
                           search=search)


@app.route('/quiz/<int:quiz_id>/join-public', methods=['POST'])
@login_required
def join_public_quiz(quiz_id):
    """Join a public quiz directly without needing a join code."""
    quiz = Quiz.query.get_or_404(quiz_id)

    if not quiz.is_public:
        flash('This quiz is not public.', 'danger')
        return redirect(url_for('quiz_listing'))
    if not quiz.is_active:
        flash('This quiz is not currently active.', 'danger')
        return redirect(url_for('quiz_listing'))
    if quiz.creator_id == current_user.id:
        flash('You cannot take your own quiz.', 'warning')
        return redirect(url_for('quiz_listing'))

    existing = Attempt.query.filter_by(quiz_id=quiz.id, user_id=current_user.id).first()
    if existing:
        if existing.is_submitted and not quiz.allow_multiple_attempts:
            flash('You have already completed this quiz.', 'warning')
            return redirect(url_for('quiz_result', attempt_id=existing.id))
        elif not existing.is_submitted:
            return redirect(url_for('take_quiz', attempt_id=existing.id))

    attempt = Attempt(
        quiz_id=quiz.id,
        user_id=current_user.id,
        total=quiz.total_questions,
        is_submitted=False
    )
    db.session.add(attempt)
    db.session.commit()
    return redirect(url_for('take_quiz', attempt_id=attempt.id))


# ─────────────────────────────────────────────
# AI EXPLANATION ENDPOINT
# ─────────────────────────────────────────────

@app.route('/api/explain/<int:question_id>')
@login_required
def api_explain(question_id):
    """
    Returns explanation for a question.
    - If creator wrote one: returns it immediately.
    - If blank: calls Gemini, caches result, returns it.
    - If AI fails: returns empty so UI degrades gracefully.
    """
    question = Question.query.get_or_404(question_id)

    # Security: only participants who attempted this quiz or the creator can fetch
    quiz = question.quiz
    is_creator = quiz.creator_id == current_user.id
    has_attempt = Attempt.query.filter_by(
        quiz_id=quiz.id, user_id=current_user.id, is_submitted=True
    ).first()
    if not is_creator and not has_attempt:
        abort(403)

    # Already have an explanation — return it
    if question.explanation:
        return jsonify({
            'explanation': question.explanation,
            'is_ai': bool(question.explanation_is_ai)
        })

    # Try to generate with Groq
    correct_option = next((o for o in question.options if o.is_correct), None)
    if not correct_option:
        return jsonify({'explanation': '', 'is_ai': False})

    if not os.environ.get('GROQ_API_KEY', ''):
        return jsonify({'explanation': '', 'is_ai': False})

    try:
        prompt = (
            "You are a quiz explanation assistant. "
            "Given a multiple choice question and its correct answer, "
            "write a clear 1-2 sentence explanation of WHY that answer is correct. "
            "Be concise, factual, and educational. No filler phrases.\n\n"
            f"Question: {question.question_text}\n"
            f"Correct Answer: {correct_option.option_text}\n"
            "Explanation:"
        )
        explanation = _call_groq(prompt)

        if explanation:
            question.explanation = explanation
            question.explanation_is_ai = True
            db.session.commit()
            logger.info(f'Groq explanation generated for question {question_id}')
            return jsonify({'explanation': explanation, 'is_ai': True})
        else:
            return jsonify({'explanation': '', 'is_ai': False})

    except Exception as e:
        logger.warning(f'Groq explanation failed for question {question_id}: {e}')
        return jsonify({'explanation': '', 'is_ai': False})

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403, message='Access denied.'), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, message='Page not found.'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', code=500, message='Something went wrong.'), 500


if __name__ == '__main__':
    app.run(debug=True)
