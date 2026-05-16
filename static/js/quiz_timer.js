/**
 * ThinkSprint Quiz Timer
 * Handles per-question countdown, answer tracking, and final submission.
 */

// ─── State ───────────────────────────────────────────────────────────────────
let currentIndex = 0;
let selectedOptionId = null;
let questionStartTime = null;
let questionTimer = null;
let globalStartTime = Date.now();
let globalTimerInterval = null;
let timeRemaining = TIMER_PER_QUESTION;

// Stores answers: { question_id, selected_option_id, time_taken_seconds }
const answers = [];

// Build a flat questions array from Jinja-passed data
// QUESTIONS is injected by the template as JSON
const questions = QUESTIONS;

// ─── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  startGlobalTimer();
  loadQuestion(0);
});

// ─── Global Timer ─────────────────────────────────────────────────────────────
function startGlobalTimer() {
  globalTimerInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - globalStartTime) / 1000);
    document.getElementById('globalTimer').textContent = `Total: ${elapsed}s`;
  }, 1000);
}

// ─── Load Question ────────────────────────────────────────────────────────────
function loadQuestion(index) {
  if (index >= questions.length) {
    submitQuiz();
    return;
  }

  currentIndex = index;
  selectedOptionId = null;
  timeRemaining = TIMER_PER_QUESTION;
  questionStartTime = Date.now();

  const q = questions[index];

  // Update counter and progress bar
  document.getElementById('questionCounter').textContent =
    `Question ${index + 1} of ${TOTAL_QUESTIONS}`;
  const pct = ((index + 1) / TOTAL_QUESTIONS) * 100;
  document.getElementById('progressBar').style.width = `${pct}%`;

  // Question text
  document.getElementById('questionText').textContent = q.question_text;

  // Question image
  const imgWrap = document.getElementById('questionImageWrap');
  const img = document.getElementById('questionImage');
  if (q.image_path) {
    img.src = `/static/uploads/${q.image_path}`;
    imgWrap.classList.remove('hidden');
  } else {
    img.src = '';
    imgWrap.classList.add('hidden');
  }

  // Options
  const container = document.getElementById('optionsContainer');
  container.innerHTML = '';
  q.options.forEach(opt => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className =
      'w-full text-left px-4 py-3 rounded-xl border-2 border-gray-200 text-sm font-medium ' +
      'text-gray-800 hover:border-indigo-400 hover:bg-indigo-50 transition option-btn';
    btn.dataset.optionId = opt.id;
    btn.textContent = opt.option_text;
    btn.onclick = () => selectOption(btn, opt.id);
    container.appendChild(btn);
  });

  // Update next button label
  const nextBtn = document.getElementById('nextBtn');
  nextBtn.textContent = index === questions.length - 1 ? 'Submit Quiz ✓' : 'Next Question →';

  // Start per-question timer
  startQuestionTimer();
}

// ─── Option Selection ─────────────────────────────────────────────────────────
function selectOption(btn, optionId) {
  // Deselect all
  document.querySelectorAll('.option-btn').forEach(b => {
    b.classList.remove('border-indigo-500', 'bg-indigo-50', 'text-indigo-700');
    b.classList.add('border-gray-200');
  });

  // Select clicked
  btn.classList.add('border-indigo-500', 'bg-indigo-50', 'text-indigo-700');
  btn.classList.remove('border-gray-200');
  selectedOptionId = optionId;
}

// ─── Answered Counter ─────────────────────────────────────────────────────────
function updateAnsweredCounter() {
  const answered = answers.filter(a => a.selected_option_id !== null).length;
  const el = document.getElementById('answeredCounter');
  if (el) {
    el.innerHTML = `
      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
      </svg>
      ${answered} / ${TOTAL_QUESTIONS} answered`;
  }
}
// ─── Per-Question Timer ───────────────────────────────────────────────────────
function startQuestionTimer() {
  clearInterval(questionTimer);
  updateTimerDisplay(TIMER_PER_QUESTION);

  questionTimer = setInterval(() => {
    timeRemaining--;
    updateTimerDisplay(timeRemaining);

    if (timeRemaining <= 0) {
      clearInterval(questionTimer);
      // Auto-advance: save whatever is selected (or null)
      saveAnswer(true);
    }
  }, 1000);
}

function updateTimerDisplay(seconds) {
  const display = document.getElementById('timerDisplay');
  const bar = document.getElementById('timerBar');

  display.textContent = seconds;

  const pct = (seconds / TIMER_PER_QUESTION) * 100;
  bar.style.width = `${pct}%`;

  // Color feedback
  if (seconds <= 5) {
    display.className = 'text-2xl font-extrabold text-red-600 tabular-nums';
    bar.className = 'bg-red-500 h-1.5 rounded-full transition-all duration-1000';
  } else if (seconds <= 10) {
    display.className = 'text-2xl font-extrabold text-orange-500 tabular-nums';
    bar.className = 'bg-orange-400 h-1.5 rounded-full transition-all duration-1000';
  } else {
    display.className = 'text-2xl font-extrabold text-indigo-600 tabular-nums';
    bar.className = 'bg-indigo-500 h-1.5 rounded-full transition-all duration-1000';
  }
}

// ─── Save Answer & Advance ────────────────────────────────────────────────────
function saveAnswer(autoAdvance = false) {
  clearInterval(questionTimer);

  const q = questions[currentIndex];
  const timeTaken = Math.floor((Date.now() - questionStartTime) / 1000);

  answers.push({
    question_id: q.id,
    selected_option_id: selectedOptionId,   // null if unanswered
    time_taken_seconds: timeTaken
  });

  if (autoAdvance) {
    // Brief visual feedback before moving on
    setTimeout(() => loadQuestion(currentIndex + 1), 600);
  }
  updateAnsweredCounter();
}

// ─── Next Button ──────────────────────────────────────────────────────────────
function nextQuestion() {
  saveAnswer(false);

  // On the last question, check for unanswered before submitting
  if (currentIndex + 1 >= questions.length) {
    const unanswered = answers.filter(a => a.selected_option_id === null).length;
    // Also count the current question if nothing selected
    const currentUnanswered = selectedOptionId === null ? 1 : 0;
    // answers array has currentIndex entries (current not yet saved), so check saved + current
    const totalUnanswered = answers.filter(a => a.selected_option_id === null).length;

    if (totalUnanswered > 0) {
      showUnansweredModal(totalUnanswered);
      return;
    }
  }

  loadQuestion(currentIndex + 1);
}

// ─── Unanswered Modal ─────────────────────────────────────────────────────────
function showUnansweredModal(count) {
  const modal = document.getElementById('unansweredModal');
  const msg   = document.getElementById('unansweredMsg');
  if (!modal) { loadQuestion(currentIndex + 1); return; }
  msg.textContent = count === 1
    ? 'You have 1 unanswered question. Skipped questions are marked as wrong. Do you want to go back or submit anyway?'
    : `You have ${count} unanswered questions. Skipped questions are marked as wrong. Do you want to go back or submit anyway?`;
  modal.classList.remove('hidden');
  modal.classList.add('flex');
}

function closeUnansweredModal() {
  const modal = document.getElementById('unansweredModal');
  if (modal) { modal.classList.add('hidden'); modal.classList.remove('flex'); }
  // Restart the timer for the current question
  startQuestionTimer();
}

function confirmSubmit() {
  const modal = document.getElementById('unansweredModal');
  if (modal) { modal.classList.add('hidden'); modal.classList.remove('flex'); }
  loadQuestion(currentIndex + 1);  // this triggers submitQuiz() since index >= length
}

// ─── Submit Quiz ──────────────────────────────────────────────────────────────
function submitQuiz() {
  clearInterval(questionTimer);
  clearInterval(globalTimerInterval);

  const totalTime = Math.floor((Date.now() - globalStartTime) / 1000);

  // Disable next button to prevent double submit
  const nextBtn = document.getElementById('nextBtn');
  if (nextBtn) {
    nextBtn.disabled = true;
    nextBtn.innerHTML = '<span class="spinner"></span>Submitting...';
    nextBtn.classList.add('opacity-75', 'cursor-not-allowed');
  }

  // Show hamster overlay while server calculates score
  if (typeof showHamster === 'function') {
    showHamster('Crunching your answers...');
  }

  fetch(SUBMIT_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers, total_time: totalTime })
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        markSubmitted();
        // Keep hamster running for at least 3 s before redirecting
        if (typeof showHamster === 'function') {
          showHamster('Calculating your score...');
        }
        setTimeout(() => {
          window.location.href = data.redirect;
        }, 2000);
      } else {
        if (typeof hideHamster === 'function') hideHamster();
        alert('Submission failed. Please try again.');
        if (nextBtn) nextBtn.disabled = false;
      }
    })
    .catch(() => {
      if (typeof hideHamster === 'function') hideHamster();
      alert('Network error. Please check your connection.');
      if (nextBtn) nextBtn.disabled = false;
    });
}
