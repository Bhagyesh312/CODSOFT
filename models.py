from datetime import datetime, timezone, date, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # ── Streak tracking ────────────────────────────────────────────────────────
    current_streak = db.Column(db.Integer, default=0)       # consecutive days with ≥1 quiz
    longest_streak = db.Column(db.Integer, default=0)       # all-time best streak
    last_quiz_date = db.Column(db.Date, nullable=True)      # date of last submitted attempt

    quizzes = db.relationship('Quiz', backref='creator', lazy=True, foreign_keys='Quiz.creator_id')
    attempts = db.relationship('Attempt', backref='user', lazy=True)
    badges = db.relationship('UserBadge', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def update_streak(self):
        """Call after a quiz is submitted. Updates current/longest streak."""
        today = datetime.now(timezone.utc).date()
        if self.last_quiz_date is None:
            self.current_streak = 1
        elif self.last_quiz_date == today:
            pass  # already counted today
        elif self.last_quiz_date == today - timedelta(days=1):
            self.current_streak = (self.current_streak or 0) + 1
        else:
            self.current_streak = 1  # streak broken

        self.last_quiz_date = today
        if (self.current_streak or 0) > (self.longest_streak or 0):
            self.longest_streak = self.current_streak

    def has_badge(self, badge_key):
        return any(b.badge_key == badge_key for b in self.badges)

    def __repr__(self):
        return f'<User {self.email}>'


# ── Badge catalogue ────────────────────────────────────────────────────────────
BADGE_DEFINITIONS = {
    'perfect_score': {
        'name': 'Perfect Score',
        'description': 'Scored 100% on a quiz',
        'color': 'gold',          # used in template to pick glow class
    },
    'speed_demon': {
        'name': 'Speed Demon',
        'description': 'Finished in the fastest 25% of all participants on a quiz',
        'color': 'cyan',
    },
    'quiz_veteran': {
        'name': 'Quiz Veteran',
        'description': 'Completed 10 or more quizzes',
        'color': 'purple',
    },
    'streak_master': {
        'name': 'Streak Master',
        'description': 'Maintained a 3-day daily quiz streak',
        'color': 'orange',
    },
    'top_scholar': {
        'name': 'Top Scholar',
        'description': 'Ranked #1 on any quiz leaderboard',
        'color': 'amber',
    },
}


class UserBadge(db.Model):
    __tablename__ = 'user_badges'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    badge_key = db.Column(db.String(50), nullable=False)
    earned_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint('user_id', 'badge_key', name='uq_user_badge'),)

    def __repr__(self):
        return f'<UserBadge {self.badge_key} user={self.user_id}>'


class Quiz(db.Model):
    __tablename__ = 'quizzes'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    join_code = db.Column(db.String(6), unique=True, nullable=True)
    code_expires_at = db.Column(db.DateTime, nullable=True)
    join_window_minutes = db.Column(db.Integer, default=10)               # configurable: 5/10/30/60
    timer_per_question = db.Column(db.Integer, default=30)
    allow_multiple_attempts = db.Column(db.Boolean, default=False)
    bonus_enabled = db.Column(db.Boolean, default=True)
    bonus_points = db.Column(db.Integer, default=2)
    shuffle_questions = db.Column(db.Boolean, default=True)
    negative_marking = db.Column(db.Boolean, default=False)              # enable/disable
    negative_penalty = db.Column(db.Float, default=0.5)                  # points deducted per wrong answer
    is_public = db.Column(db.Boolean, default=False)                     # show on public quiz listing
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    questions = db.relationship('Question', backref='quiz', lazy=True, cascade='all, delete-orphan')
    attempts = db.relationship('Attempt', backref='quiz', lazy=True, cascade='all, delete-orphan')

    @property
    def has_attempts(self):
        return len(self.attempts) > 0

    @property
    def join_code_valid(self):
        if not self.code_expires_at or not self.is_active:
            return False
        return datetime.now(timezone.utc) < self.code_expires_at.replace(tzinfo=timezone.utc)

    @property
    def total_questions(self):
        return len(self.questions)

    def __repr__(self):
        return f'<Quiz {self.title}>'


class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(300), nullable=True)
    order_index = db.Column(db.Integer, default=0)
    explanation = db.Column(db.Text, nullable=True)        # optional explanation shown after submission
    explanation_is_ai = db.Column(db.Boolean, default=False)  # True if AI-generated

    options = db.relationship('Option', backref='question', lazy=True, cascade='all, delete-orphan')
    attempt_answers = db.relationship('AttemptAnswer', backref='question', lazy=True)

    def __repr__(self):
        return f'<Question {self.id}>'


class Option(db.Model):
    __tablename__ = 'options'

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    option_text = db.Column(db.String(500), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Option {self.id} correct={self.is_correct}>'


class Attempt(db.Model):
    __tablename__ = 'attempts'

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    score = db.Column(db.Integer, default=0)                             # raw correct count
    penalty = db.Column(db.Float, default=0.0)                          # total penalty deducted
    total = db.Column(db.Integer, default=0)
    time_taken = db.Column(db.Integer, default=0)
    bonus_points = db.Column(db.Integer, default=0)
    is_submitted = db.Column(db.Boolean, default=False)
    taken_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    answers = db.relationship('AttemptAnswer', backref='attempt', lazy=True, cascade='all, delete-orphan')

    @property
    def net_score(self):
        """Score after applying negative marking penalty."""
        return max(0.0, self.score - self.penalty)

    @property
    def final_score(self):
        return round(self.net_score + self.bonus_points, 2)

    @property
    def percentage(self):
        if self.total == 0:
            return 0
        return round((self.net_score / self.total) * 100, 1)

    def __repr__(self):
        return f'<Attempt {self.id} score={self.score} penalty={self.penalty}>'


class AttemptAnswer(db.Model):
    __tablename__ = 'attempt_answers'

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('attempts.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    selected_option_id = db.Column(db.Integer, db.ForeignKey('options.id'), nullable=True)
    is_correct = db.Column(db.Boolean, default=False)
    time_taken_seconds = db.Column(db.Integer, default=0)

    selected_option = db.relationship('Option', foreign_keys=[selected_option_id])

    def __repr__(self):
        return f'<AttemptAnswer q={self.question_id} correct={self.is_correct}>'
