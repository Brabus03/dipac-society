const eventModal = document.querySelector('#event-modal');
const loginModal = document.querySelector('#login-modal');
const navToggle = document.querySelector('#nav-toggle');
const primaryNav = document.querySelector('#primary-nav');

if (navToggle && primaryNav) {
  navToggle.addEventListener('click', () => {
    const isOpen = primaryNav.classList.toggle('nav-open');
    navToggle.setAttribute('aria-expanded', String(isOpen));
    navToggle.setAttribute('aria-label', isOpen ? 'Close menu' : 'Open menu');
  });
  primaryNav.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
    primaryNav.classList.remove('nav-open');
    navToggle.setAttribute('aria-expanded', 'false');
    navToggle.setAttribute('aria-label', 'Open menu');
  }));
}

const stories = {
  dentratnf: { kicker: 'EVENT 01 · SEMARANG', title: 'Dentra TNF Semarang', copy: 'Dentra throwback 1990–2026, Basement Groove Underground Party. Lihat poster, teaser, dan recap di bawah.', images: ['assets/dentra-poster.png', 'assets/dentra-recap.png'], links: [['Event poster', 'https://www.instagram.com/p/DXeWAAfCUMI/?igsh=a2xpNXB2eDh5cjVn'], ['Video teaser', 'https://www.instagram.com/reel/DXjkKoTic75/?igsh=a21id2ZwYmVqNHV2'], ['Photo recap', 'https://www.instagram.com/p/DX_m0-iCXL3/?igsh=MXRxZ3pmMGZwOWNqaQ=='], ['Video recap', 'https://www.instagram.com/reel/DYDFxS5yBQK/?igsh=MTA4MTBsNWRpN3Bvag==']] },
  midnight: { kicker: 'EVENT 02 · SEMARANG', title: 'Midnight In Cell Soci Semarang', copy: 'Dentra Midnight In Cell, Vol. 2 di Soci Club Semarang. Lihat poster, teaser, dan recap di bawah.', images: ['assets/midnight-poster.png', 'assets/midnight-recap.png'], links: [['Event post', 'https://www.instagram.com/p/DYUMJ3difSd/?igsh=MXVzdXl5bml2amI0NA=='], ['Video teaser', 'https://www.instagram.com/reel/DYRyqVXpOE2/?igsh=a3R6cHB1eHNnN3lz'], ['Photo recap', 'https://www.instagram.com/p/DYrv6gpCXgJ/?igsh=ZWMxZnNjb3Z1bDU2'], ['Video recap', 'https://www.instagram.com/reel/DYuOfp_vZ5p/?igsh=MTlpbzdxcHhtOWJnNw==']] },
  coming: { kicker: 'UPCOMING EVENT · 23 JULY 2026', title: 'White Party', copy: 'For information & Guestlist, isi form di bawah ini. White Party di STALK SCBD, Jakarta — Save the date: 23 July 2026.', images: ['assets/white-party-stalk-poster.png'], links: [], form: 'https://docs.google.com/forms/d/e/1FAIpQLSeb9XSSOfgZnaNkXUhtD-r_pSoZyqUM9uvPR9oFerHOsDcuCA/viewform' }
};

function openModal(modal) { modal.classList.add('open'); modal.setAttribute('aria-hidden', 'false'); document.body.style.overflow = 'hidden'; }
function closeModal(modal) { modal.classList.remove('open'); modal.setAttribute('aria-hidden', 'true'); document.body.style.overflow = ''; }

document.querySelectorAll('[data-event]').forEach(card => card.addEventListener('click', () => {
  const story = stories[card.dataset.event];
  if (!story) return;
  document.querySelector('#modal-kicker').textContent = story.kicker;
  document.querySelector('#modal-title').textContent = story.title;
  document.querySelector('#modal-copy').textContent = story.copy;
  document.querySelector('#modal-gallery').innerHTML = story.images.map((src, i) => `<img src="${src}" alt="${story.title} visual ${i + 1}">`).join('');
  const modalLinks = document.querySelector('#modal-links');
  modalLinks.hidden = story.links.length === 0;
  modalLinks.innerHTML = story.links.map(([label, href]) => `<a href="${href}" target="_blank" rel="noopener noreferrer">${label} <span>↗</span></a>`).join('');
  const modalForm = document.querySelector('#modal-form');
  modalForm.hidden = !story.form;
  modalForm.innerHTML = story.form
    ? `<p class="modal-form-label">For information &amp; Guestlist</p><a class="modal-form-button" href="${story.form}" target="_blank" rel="noopener noreferrer">Isi Guestlist Form <span>↗</span></a>`
    : '';
  openModal(eventModal);
}));

document.querySelectorAll('[data-open-login]').forEach(btn => btn.addEventListener('click', () => openModal(loginModal)));
document.querySelectorAll('[data-close]').forEach(btn => btn.addEventListener('click', () => closeModal(btn.closest('.modal'))));
document.querySelectorAll('.modal').forEach(modal => modal.addEventListener('click', e => { if (e.target === modal) closeModal(modal); }));
document.addEventListener('keydown', e => { if (e.key === 'Escape') document.querySelectorAll('.modal.open').forEach(closeModal); });

const loginState = new URLSearchParams(window.location.search).get('login');
if (loginState === 'error' || loginState === 'required') {
  openModal(loginModal);
  document.querySelector('#form-note').textContent = loginState === 'error' ? 'Email atau password tidak sesuai.' : 'Silakan masuk untuk membuka dashboard.';
}

// =================
// HERO 3D PARALLAX (mouse-tracking orb/glow depth)
// =================
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const hero = document.querySelector('.hero');

if (hero && !reduceMotion) {
  const glows = hero.querySelectorAll('.hero-glow');
  const orbs = hero.querySelectorAll('.orb');
  const heroContent = hero.querySelector('.hero-content');

  hero.addEventListener('mousemove', event => {
    const rect = hero.getBoundingClientRect();
    // -1..1 range from hero center, used to drive both translation depth and tilt
    const px = ((event.clientX - rect.left) / rect.width - 0.5) * 2;
    const py = ((event.clientY - rect.top) / rect.height - 0.5) * 2;

    // Glows sit furthest back - smallest movement (background parallax layer)
    glows.forEach((glow, i) => {
      const depth = 10 + i * 4;
      glow.style.transform = `translate3d(${px * depth}px, ${py * depth}px, 0)`;
    });

    // Orbs float in the middle layer - larger movement than glows
    orbs.forEach((orb, i) => {
      const depth = 24 + i * 10;
      orb.style.transform = `translate3d(${px * depth}px, ${py * depth}px, 0)`;
    });

    // Headline gets a very subtle 3D tilt for depth, like it's floating in space
    if (heroContent) {
      heroContent.style.transform = `perspective(1200px) rotateY(${px * 3}deg) rotateX(${-py * 3}deg)`;
    }
  });

  hero.addEventListener('mouseleave', () => {
    glows.forEach(glow => { glow.style.transform = ''; });
    orbs.forEach(orb => { orb.style.transform = ''; });
    if (heroContent) heroContent.style.transform = '';
  });
}

// =================
// EVENT CARD 3D TILT (mouse-tracking perspective + light sheen)
// =================
if (!reduceMotion) {
  document.querySelectorAll('.event-card').forEach(card => {
    card.style.transformStyle = 'preserve-3d';

    card.addEventListener('mousemove', event => {
      const rect = card.getBoundingClientRect();
      const px = (event.clientX - rect.left) / rect.width;
      const py = (event.clientY - rect.top) / rect.height;
      const rotateY = (px - 0.5) * 14;
      const rotateX = (0.5 - py) * 14;

      card.style.transform = `perspective(900px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02,1.02,1.02)`;
      card.style.setProperty('--sheen-x', `${px * 100}%`);
      card.style.setProperty('--sheen-y', `${py * 100}%`);
    });

    card.addEventListener('mouseleave', () => {
      card.style.transform = '';
    });
  });
}

document.querySelector('#login-form').addEventListener('submit', async event => {
  event.preventDefault();
  const form = event.currentTarget;
  const note = document.querySelector('#form-note');
  const submitButton = form.querySelector('button');
  const email = form.elements.email.value.trim().toLowerCase();
  const password = form.elements.password.value;

  submitButton.disabled = true;
  const originalLabel = submitButton.innerHTML;
  submitButton.innerHTML = 'Checking access...';

  try {
    const response = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Login gagal');
    window.location.href = '/dashboard';
  } catch (error) {
    note.textContent = error.message;
    submitButton.disabled = false;
    submitButton.innerHTML = originalLabel;
  }
});
