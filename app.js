
const nav = document.getElementById('nav')
const burger = document.getElementById('burger')
const modalBackdrop = document.getElementById('modalBackdrop')
const modalClose = document.getElementById('modalClose')
const toast = document.getElementById('toast')

const go = id => {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  nav.classList.remove('open')
}

document.querySelectorAll('[data-go]').forEach(btn => {
  btn.addEventListener('click', () => go(btn.dataset.go))
})

burger.addEventListener('click', () => nav.classList.toggle('open'))

const onScroll = () => document.body.classList.toggle('scrolled', window.scrollY > 40)
onScroll()
window.addEventListener('scroll', onScroll, { passive: true })

const observer = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) entry.target.classList.add('is-visible')
  })
}, { threshold: 0.12 })
document.querySelectorAll('.reveal').forEach(el => observer.observe(el))

document.querySelectorAll('.js-modal-open').forEach(btn => {
  btn.addEventListener('click', () => {
    modalBackdrop.hidden = false
    document.body.style.overflow = 'hidden'
  })
})
const closeModal = () => {
  modalBackdrop.hidden = true
  document.body.style.overflow = ''
}
modalClose.addEventListener('click', closeModal)
modalBackdrop.addEventListener('mousedown', e => {
  if (e.target === modalBackdrop) closeModal()
})
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && !modalBackdrop.hidden) closeModal()
})

const filterButtons = [...document.querySelectorAll('#filters button')]
const portfolioCards = [...document.querySelectorAll('.portfolioCard')]
filterButtons.forEach(btn => btn.addEventListener('click', () => {
  filterButtons.forEach(x => x.classList.remove('active'))
  btn.classList.add('active')
  const filter = btn.dataset.filter
  portfolioCards.forEach(card => {
    const match = filter === 'Все' || card.dataset.tag === filter
    card.style.display = match ? '' : 'none'
  })
}))

const quizQuestions = [
  { q:'Какой образ вам ближе?', options:[['Нежный и натуральный','nude'],['Чистый минимализм','minimal'],['Яркий цвет','color'],['Акцентный nail art','art']] },
  { q:'Какую длину вы носите чаще?', options:[['Короткую','short'],['Среднюю','medium'],['Длинную','long'],['Меняю под настроение','mix']] },
  { q:'Что важнее в дизайне?', options:[['Универсальность','daily'],['Необычная деталь','detail'],['Трендовый цвет','trend'],['Вау-эффект','wow']] }
]
const quizResults = {
  nude:{title:'Soft Nude',text:'Молочная или полупрозрачная база, мягкий квадрат и деликатный глянец.',image:'/assets/nail-polish.webp'},
  minimal:{title:'Clean Lines',text:'Нюдовая база, тонкая геометрия и один аккуратный акцент.',image:'/assets/nail-lines.webp'},
  color:{title:'Color Mood',text:'Чистый насыщенный оттенок с идеальным бликом и архитектурой.',image:'/assets/pink-nails.webp'},
  art:{title:'Art Accent',text:'Выразительный nail art с ручной прорисовкой и индивидуальной композицией.',image:'/assets/pink-process.webp'}
}
let quizStep = 0
let quizAnswers = []
const quizCard = document.getElementById('quizCard')
const quizMediaImage = document.getElementById('quizMediaImage')

function renderQuiz() {
  if (quizStep < quizQuestions.length) {
    const item = quizQuestions[quizStep]
    quizCard.innerHTML = `
      <span class="kicker dark">Подбор дизайна</span>
      <div class="quizProgress"><i style="width:${((quizStep + 1) / quizQuestions.length) * 100}%"></i></div>
      <small>Шаг ${quizStep + 1} из ${quizQuestions.length}</small>
      <h2>${item.q}</h2>
      <div class="quizOptions">
        ${item.options.map(([label, value]) => `<button data-quiz="${value}">${label}<span>→</span></button>`).join('')}
      </div>`
    quizCard.querySelectorAll('[data-quiz]').forEach(btn => btn.addEventListener('click', () => {
      quizAnswers.push(btn.dataset.quiz)
      quizStep++
      renderQuiz()
    }))
  } else {
    const result = quizResults[quizAnswers[0] || 'nude']
    quizMediaImage.src = result.image
    quizCard.innerHTML = `
      <span class="kicker dark">Ваше направление</span>
      <h2>${result.title}</h2>
      <div class="quizResult"><img src="${result.image}" alt="${result.title}"><p>${result.text}</p></div>
      <div class="quizButtons"><button class="primary js-quiz-book">Записаться с этим дизайном</button><button class="textButton" id="quizReset">Пройти заново</button></div>`
    quizCard.querySelector('.js-quiz-book').addEventListener('click', () => {
      modalBackdrop.hidden = false
      document.body.style.overflow = 'hidden'
    })
    quizCard.querySelector('#quizReset').addEventListener('click', () => {
      quizStep = 0
      quizAnswers = []
      quizMediaImage.src = '/assets/nail-polish.webp'
      renderQuiz()
    })
  }
}
renderQuiz()

const reviews = [
  {name:'Марина', text:'Очень аккуратный маникюр и идеальное выравнивание. Через три недели покрытие выглядит свежо, ни одного скола.'},
  {name:'София', text:'Пришла со сложным референсом — мастер повторила дизайн точь-в-точь, но адаптировала под мою форму ногтей. Восторг.'},
  {name:'Алина', text:'Нравится стерильность, спокойная атмосфера и то, что запись всегда начинается вовремя. Теперь только сюда.'},
  {name:'Екатерина', text:'Самый тонкий и красивый френч, который мне делали. Отдельное спасибо за бережную обработку кутикулы.'}
]
let reviewIndex = 0
const reviewText = document.getElementById('reviewText')
const reviewName = document.getElementById('reviewName')
const reviewAvatar = document.getElementById('reviewAvatar')
const reviewDots = document.getElementById('reviewDots')

function renderReview() {
  const item = reviews[reviewIndex]
  reviewText.textContent = `«${item.text}»`
  reviewName.textContent = item.name
  reviewAvatar.textContent = item.name[0]
  reviewDots.innerHTML = reviews.map((_, i) => `<button class="${i === reviewIndex ? 'active' : ''}" data-review="${i}"></button>`).join('')
  reviewDots.querySelectorAll('button').forEach(btn => btn.addEventListener('click', () => {
    reviewIndex = Number(btn.dataset.review)
    renderReview()
  }))
}
document.getElementById('reviewPrev').addEventListener('click', () => { reviewIndex = (reviewIndex - 1 + reviews.length) % reviews.length; renderReview() })
document.getElementById('reviewNext').addEventListener('click', () => { reviewIndex = (reviewIndex + 1) % reviews.length; renderReview() })
renderReview()
setInterval(() => { reviewIndex = (reviewIndex + 1) % reviews.length; renderReview() }, 5200)

function showToast(message) {
  toast.textContent = message
  toast.hidden = false
  setTimeout(() => { toast.hidden = true }, 5000)
}

document.querySelectorAll('.js-booking-form').forEach(form => {
  form.addEventListener('submit', async e => {
    e.preventDefault()
    const submitButton = form.querySelector('button[type="submit"], button:not([type])')
    const oldText = submitButton.textContent
    submitButton.disabled = true
    submitButton.textContent = 'Отправляем…'

    const data = Object.fromEntries(new FormData(form).entries())
    try {
      const response = await fetch('/api/booking', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })
      if (!response.ok) throw new Error('Request failed')
      form.reset()
      closeModal()
      showToast('Запись отправлена ✨ Администратор свяжется с вами для подтверждения.')
    } catch {
      showToast('Не удалось отправить форму. Позвоните нам: +7 (999) 310-18-18')
    } finally {
      submitButton.disabled = false
      submitButton.textContent = oldText
    }
  })
})
