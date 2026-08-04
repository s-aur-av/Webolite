/* ============================================
   Webolite — Premium Agency Website
   Vanilla JavaScript · No dependencies
   ============================================ */

(function () {
  'use strict';

  /* ----- Loader ----- */
  const loader = document.getElementById('loader');
  window.addEventListener('load', () => {
    setTimeout(() => {
      loader.classList.add('hidden');
      document.body.style.overflow = '';
    }, 1400);
  });

  /* ----- Scroll Progress ----- */
  const scrollProgress = document.getElementById('scrollProgress');
  function updateScrollProgress() {
    const scrollTop = window.scrollY;
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const progress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
    scrollProgress.style.width = progress + '%';
  }

  /* ----- Sticky Header ----- */
  const header = document.getElementById('header');
  function updateHeader() {
    if (window.scrollY > 40) {
      header.classList.add('scrolled');
    } else {
      header.classList.remove('scrolled');
    }
  }

  /* ----- Back to Top ----- */
  const backToTop = document.getElementById('backToTop');
  function updateBackToTop() {
    if (window.scrollY > 600) {
      backToTop.classList.add('visible');
    } else {
      backToTop.classList.remove('visible');
    }
  }

  backToTop.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  /* ----- Active Nav Highlight ----- */
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('.nav-link');

  function updateActiveNav() {
    const scrollY = window.scrollY + 120;
    let current = '';
    sections.forEach((section) => {
      const top = section.offsetTop;
      const height = section.offsetHeight;
      if (scrollY >= top && scrollY < top + height) {
        current = section.getAttribute('id');
      }
    });
    navLinks.forEach((link) => {
      link.classList.remove('active');
      if (link.getAttribute('href') === '#' + current) {
        link.classList.add('active');
      }
    });
  }

  /* ----- Scroll Handler ----- */
  let ticking = false;
  window.addEventListener('scroll', () => {
    if (!ticking) {
      requestAnimationFrame(() => {
        updateScrollProgress();
        updateHeader();
        updateBackToTop();
        updateActiveNav();
        ticking = false;
      });
      ticking = true;
    }
  }, { passive: true });

  /* ----- Mobile Menu ----- */
  const hamburger = document.getElementById('hamburger');
  const navMenu = document.getElementById('navMenu');
  let overlay = document.querySelector('.nav-overlay');

  if (!overlay) {
    overlay = document.createElement('div');
    overlay.className = 'nav-overlay';
    document.body.appendChild(overlay);
  }

  function toggleMenu() {
    const isOpen = navMenu.classList.toggle('active');
    hamburger.classList.toggle('active');
    overlay.classList.toggle('active');
    hamburger.setAttribute('aria-expanded', isOpen);
    document.body.style.overflow = isOpen ? 'hidden' : '';
  }

  hamburger.addEventListener('click', toggleMenu);
  overlay.addEventListener('click', toggleMenu);

  navLinks.forEach((link) => {
    link.addEventListener('click', () => {
      if (navMenu.classList.contains('active')) {
        toggleMenu();
      }
    });
  });

  /* ----- Theme Toggle ----- */
  const themeToggle = document.getElementById('themeToggle');
  function safeStorageGet(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  }
  function safeStorageSet(key, val) {
    try { localStorage.setItem(key, val); } catch (e) {}
  }
  const savedTheme = safeStorageGet('webolite-theme');
  if (savedTheme === 'light') {
    document.documentElement.setAttribute('data-theme', 'light');
  } else {
    document.documentElement.removeAttribute('data-theme');
  }

  themeToggle.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'light' ? 'dark' : 'light';
    if (next === 'light') {
      document.documentElement.setAttribute('data-theme', 'light');
      safeStorageSet('webolite-theme', 'light');
    } else {
      document.documentElement.removeAttribute('data-theme');
      safeStorageSet('webolite-theme', 'dark');
    }
  });

  /* ----- Reveal on Scroll ----- */
  const revealElements = document.querySelectorAll('.reveal');
  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          revealObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
  );

  revealElements.forEach((el) => revealObserver.observe(el));

  /* ----- Counter Animation ----- */
  function animateCounter(el) {
    const target = parseInt(el.getAttribute('data-count'), 10);
    const duration = 2000;
    const start = performance.now();
    const isStatBig = el.classList.contains('stat-big') || el.classList.contains('stat-number');

    function update(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.floor(eased * target);
      el.textContent = current;
      if (progress < 1) {
        requestAnimationFrame(update);
      } else {
        el.textContent = target;
      }
    }
    requestAnimationFrame(update);
  }

  const counterEls = document.querySelectorAll('[data-count]');
  const counterObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          animateCounter(entry.target);
          counterObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.5 }
  );

  counterEls.forEach((el) => counterObserver.observe(el));

  /* ----- FAQ Accordion ----- */
  const faqItems = document.querySelectorAll('.faq-item');

  faqItems.forEach((item) => {
    const question = item.querySelector('.faq-question');
    question.addEventListener('click', () => {
      const isActive = item.classList.contains('active');
      // Close all
      faqItems.forEach((i) => {
        i.classList.remove('active');
        i.querySelector('.faq-question').setAttribute('aria-expanded', 'false');
      });
      // Open clicked if was closed
      if (!isActive) {
        item.classList.add('active');
        question.setAttribute('aria-expanded', 'true');
      }
    });
  });

  /* ----- Dynamic Portfolio (connected to Admin) ----- */
  const portfolioGrid = document.getElementById('portfolioGrid');
  const filterBtns = document.querySelectorAll('.filter-btn');

  function renderPortfolio(items) {
    if (!portfolioGrid) return;

    if (!items || items.length === 0) {
      portfolioGrid.innerHTML = '<div class="testimonial-loading" style="grid-column:1/-1">No projects yet.</div>';
      return;
    }

    portfolioGrid.innerHTML = items.map(function (p) {
      var tags = (p.tags || []).map(function (t) {
        return '<span>' + t + '</span>';
      }).join('');

      var media = '';
      if (p.image) {
        media = '<img src="' + p.image + '" alt="' + (p.title || '') + '" loading="lazy" style="width:100%;height:100%;object-fit:cover;">';
      } else {
        media = '<div class="portfolio-placeholder ' + (p.gradient || 'gradient-1') + '"><span>' + (p.title || 'Project') + '</span></div>';
      }

      return (
        '<article class="portfolio-card reveal visible" data-category="' + (p.category || '') + '">' +
          '<div class="portfolio-image">' +
            media +
            '<div class="portfolio-overlay">' +
              '<div class="portfolio-tags">' + tags + '</div>' +
              '<div class="portfolio-actions">' +
                '<a href="' + (p.demoUrl || '#') + '" class="btn btn-sm btn-primary" target="_blank" rel="noopener">Live Demo</a>' +
                '<a href="' + (p.caseUrl || '#') + '" class="btn btn-sm btn-outline" target="_blank" rel="noopener">Case Study</a>' +
              '</div>' +
            '</div>' +
          '</div>' +
          '<div class="portfolio-info">' +
            '<span class="portfolio-cat">' + (p.catLabel || 'Project') + '</span>' +
            '<h3>' + (p.title || '') + '</h3>' +
          '</div>' +
        '</article>'
      );
    }).join('');
  }

  function bindPortfolioFilters() {
    filterBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        filterBtns.forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        var filter = btn.getAttribute('data-filter');
        var cards = portfolioGrid ? portfolioGrid.querySelectorAll('.portfolio-card') : [];
        cards.forEach(function (card) {
          var categories = card.getAttribute('data-category') || '';
          if (filter === 'all' || categories.indexOf(filter) !== -1) {
            card.classList.remove('hidden');
          } else {
            card.classList.add('hidden');
          }
        });
      });
    });
  }

  var FALLBACK_PORTFOLIO = [
    { title: 'Aether Analytics Platform', category: 'web design', catLabel: 'SaaS Website', gradient: 'gradient-1', tags: ['Next.js','TypeScript','Tailwind'], image: '', demoUrl: '#', caseUrl: '#' },
    { title: 'Lumina Fashion Store', category: 'ecommerce', catLabel: 'E-commerce', gradient: 'gradient-2', tags: ['Shopify','React','Stripe'], image: '', demoUrl: '#', caseUrl: '#' },
    { title: 'Pulse Project Management', category: 'app', catLabel: 'Web Application', gradient: 'gradient-3', tags: ['React','Node.js','PostgreSQL'], image: '', demoUrl: '#', caseUrl: '#' },
    { title: 'Vertex Health Portal', category: 'design web', catLabel: 'Healthcare', gradient: 'gradient-4', tags: ['Figma','Framer','Webflow'], image: '', demoUrl: '#', caseUrl: '#' },
    { title: 'Orbit AI Assistant', category: 'app', catLabel: 'AI Product', gradient: 'gradient-5', tags: ['Vue','Python','OpenAI'], image: '', demoUrl: '#', caseUrl: '#' },
    { title: 'Nexus Enterprise Store', category: 'ecommerce design', catLabel: 'B2B Commerce', gradient: 'gradient-6', tags: ['Next.js','Shopify Plus','GraphQL'], image: '', demoUrl: '#', caseUrl: '#' }
  ];

  async function loadPortfolio() {
    if (!portfolioGrid) return;
    try {
      var res = await fetch('/api/portfolio');
      if (!res.ok) throw new Error('API ' + res.status);
      var data = await res.json();
      if (data.success && data.data && data.data.length) {
        renderPortfolio(data.data);
      } else {
        renderPortfolio(FALLBACK_PORTFOLIO);
      }
      bindPortfolioFilters();
    } catch (err) {
      console.error('Portfolio load error:', err);
      renderPortfolio(FALLBACK_PORTFOLIO);
      bindPortfolioFilters();
    }
  }

  loadPortfolio();

  /* Apply site settings from Admin → updates main website */
  async function loadSettings() {
    try {
      var res = await fetch('/api/settings');
      if (!res.ok) return;
      var data = await res.json();
      if (!data.success || !data.data) return;
      var s = data.data;

      // Hero title (supports \n line breaks, last line gets gradient)
      var titleEl = document.querySelector('.hero-title');
      if (titleEl && s.heroTitle) {
        var lines = String(s.heroTitle).replace(/\\n/g, '\n').split('\n').filter(Boolean);
        if (lines.length >= 2) {
          titleEl.innerHTML = lines.slice(0, -1).map(function (l) { return l + '<br>'; }).join('') +
            '<span class="gradient-text">' + lines[lines.length - 1] + '</span>';
        } else if (lines.length === 1) {
          titleEl.innerHTML = '<span class="gradient-text">' + lines[0] + '</span>';
        }
      }

      // Hero subtitle
      var subtitle = document.querySelector('.hero-subtitle');
      if (subtitle && s.heroSubtitle) subtitle.textContent = s.heroSubtitle;

      // All stat counters (hero + stats section)
      if (s.stats) {
        var allCounters = document.querySelectorAll('[data-count]');
        // Map: typically projects, satisfaction/clients, years depending on section
        // Hero: projects, satisfaction, years
        // Stats section: projects, clients, years, (24/7 static)
        var heroStats = document.querySelectorAll('.hero-stats [data-count]');
        if (heroStats[0] && s.stats.projects != null) {
          heroStats[0].setAttribute('data-count', s.stats.projects);
          heroStats[0].textContent = s.stats.projects;
        }
        if (heroStats[1] && s.stats.satisfaction != null) {
          heroStats[1].setAttribute('data-count', s.stats.satisfaction);
          heroStats[1].textContent = s.stats.satisfaction;
        }
        if (heroStats[2] && s.stats.years != null) {
          heroStats[2].setAttribute('data-count', s.stats.years);
          heroStats[2].textContent = s.stats.years;
        }

        var sectionStats = document.querySelectorAll('.stats-section [data-count]');
        if (sectionStats[0] && s.stats.projects != null) {
          sectionStats[0].setAttribute('data-count', s.stats.projects);
          sectionStats[0].textContent = s.stats.projects;
        }
        if (sectionStats[1] && s.stats.clients != null) {
          sectionStats[1].setAttribute('data-count', s.stats.clients);
          sectionStats[1].textContent = s.stats.clients;
        }
        if (sectionStats[2] && s.stats.years != null) {
          sectionStats[2].setAttribute('data-count', s.stats.years);
          sectionStats[2].textContent = s.stats.years;
        }
      }

      // Contact email — update all mailto links and visible text
      if (s.contactEmail) {
        document.querySelectorAll('a[href^="mailto:"]').forEach(function (a) {
          a.href = 'mailto:' + s.contactEmail;
          // Only replace if it looks like the default contact email
          if (a.textContent.indexOf('@') !== -1) {
            a.textContent = s.contactEmail;
          }
        });
      }

      // Contact phone — update all tel links and visible text
      if (s.contactPhone) {
        var telHref = 'tel:' + String(s.contactPhone).replace(/[^\d+]/g, '');
        document.querySelectorAll('a[href^="tel:"]').forEach(function (a) {
          a.href = telHref;
          a.textContent = s.contactPhone;
        });
      }
    } catch (e) {
      console.warn('Settings load skipped:', e);
    }
  }

  loadSettings();

  /* ----- Load ALL editable site content from Admin CMS ----- */
  async function loadSiteContent() {
    try {
      var res = await fetch('/api/content');
      if (!res.ok) return;
      var payload = await res.json();
      if (!payload.success || !payload.data) return;
      var c = payload.data;

      if (c.hero) {
        var badge = document.querySelector('.hero-badge');
        if (badge && c.hero.badge) badge.textContent = c.hero.badge;
        var titleEl = document.querySelector('.hero-title');
        if (titleEl && c.hero.title) {
          var lines = String(c.hero.title).replace(/\\n/g, '\n').split('\n').filter(Boolean);
          if (lines.length >= 2) {
            titleEl.innerHTML = lines.slice(0, -1).map(function (l) { return l + '<br>'; }).join('') +
              '<span class="gradient-text">' + lines[lines.length - 1] + '</span>';
          } else if (lines.length === 1) {
            titleEl.innerHTML = '<span class="gradient-text">' + lines[0] + '</span>';
          }
        }
        var sub = document.querySelector('.hero-subtitle');
        if (sub && c.hero.subtitle) sub.textContent = c.hero.subtitle;
        var ctas = document.querySelectorAll('.hero-actions .btn');
        if (ctas[0] && c.hero.ctaPrimary) {
          var svg0 = ctas[0].querySelector('svg');
          ctas[0].textContent = c.hero.ctaPrimary + ' ';
          if (svg0) ctas[0].appendChild(svg0);
        }
        if (ctas[1] && c.hero.ctaSecondary) ctas[1].textContent = c.hero.ctaSecondary;
      }

      if (c.services && c.services.length) {
        var serviceCards = document.querySelectorAll('.service-card');
        c.services.forEach(function (svc, i) {
          if (!serviceCards[i]) return;
          var h3 = serviceCards[i].querySelector('h3');
          var p = serviceCards[i].querySelector('p');
          if (h3 && svc.title) h3.textContent = svc.title;
          if (p && svc.desc) p.textContent = svc.desc;
        });
      }

      if (c.process && c.process.length) {
        var steps = document.querySelectorAll('.process-step');
        c.process.forEach(function (step, i) {
          if (!steps[i]) return;
          var num = steps[i].querySelector('.step-number');
          var h3 = steps[i].querySelector('h3');
          var p = steps[i].querySelector('p');
          if (num && step.step) num.textContent = step.step;
          if (h3 && step.title) h3.textContent = step.title;
          if (p && step.desc) p.textContent = step.desc;
        });
      }

      if (c.pricing && c.pricing.length) {
        var cards = document.querySelectorAll('.pricing-card');
        c.pricing.forEach(function (plan, i) {
          if (!cards[i]) return;
          var h3 = cards[i].querySelector('.pricing-header h3');
          var desc = cards[i].querySelector('.pricing-header p');
          var amount = cards[i].querySelector('.amount');
          var period = cards[i].querySelector('.period');
          var features = cards[i].querySelector('.pricing-features');
          var cta = cards[i].querySelector('a.btn');
          if (h3 && plan.name) h3.textContent = plan.name;
          if (desc && plan.desc) desc.textContent = plan.desc;
          if (amount && plan.price) amount.textContent = plan.price;
          if (period) period.textContent = plan.period || '';
          if (features && plan.features && plan.features.length) {
            features.innerHTML = plan.features.map(function (f) {
              return '<li><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> ' + f + '</li>';
            }).join('');
          }
          if (cta && plan.cta) cta.textContent = plan.cta;
          if (cta && plan.link) cta.setAttribute('href', plan.link);
        });
      }

      if (c.faq && c.faq.length) {
        var items = document.querySelectorAll('.faq-item');
        c.faq.forEach(function (item, i) {
          if (!items[i]) return;
          var qSpan = items[i].querySelector('.faq-question span');
          if (qSpan && item.q) qSpan.textContent = item.q;
          var aP = items[i].querySelector('.faq-answer p');
          if (aP && item.a) aP.textContent = item.a;
        });
      }

      if (c.tech && c.tech.length) {
        var techGrid = document.querySelector('.tech-grid');
        if (techGrid) {
          techGrid.innerHTML = c.tech.map(function (t) {
            return '<div class="tech-item"><span>' + t + '</span></div>';
          }).join('');
        }
      }

      if (c.cta) {
        var ctaTitle = document.querySelector('.cta-card h2');
        var ctaSub = document.querySelector('.cta-card p');
        var ctaBtn = document.querySelector('.cta-card .btn');
        if (ctaTitle && c.cta.title) ctaTitle.textContent = c.cta.title;
        if (ctaSub && c.cta.subtitle) ctaSub.textContent = c.cta.subtitle;
        if (ctaBtn && c.cta.button) {
          var svg = ctaBtn.querySelector('svg');
          ctaBtn.textContent = c.cta.button + ' ';
          if (svg) ctaBtn.appendChild(svg);
        }
      }

      if (c.footer) {
        var footDesc = document.querySelector('.footer-brand p');
        if (footDesc && c.footer.description) footDesc.textContent = c.footer.description;
      }
    } catch (err) {
      console.warn('Content load skipped:', err);
    }
  }

  loadSiteContent();

  /* ----- Dynamic Testimonials ----- */
  const track = document.getElementById('testimonialTrack');
  const prevBtn = document.getElementById('testimonialPrev');
  const nextBtn = document.getElementById('testimonialNext');
  const dotsContainer = document.getElementById('testimonialDots');
  let currentSlide = 0;
  let autoplayTimer = null;
  let totalSlides = 0;

  function starsHTML(rating) {
    return '★'.repeat(rating) + '☆'.repeat(5 - rating);
  }

  function resetAutoplay() {
    clearInterval(autoplayTimer);
    if (totalSlides > 1) {
      autoplayTimer = setInterval(() => goToSlide(currentSlide + 1), 5000);
    }
  }

  function goToSlide(index) {
    if (totalSlides === 0 || !track) return;
    currentSlide = (index + totalSlides) % totalSlides;
    track.style.transform = 'translateX(-' + currentSlide * 100 + '%)';
    if (dotsContainer) {
      dotsContainer.querySelectorAll('.dot').forEach((d, i) => {
        d.classList.toggle('active', i === currentSlide);
      });
    }
    resetAutoplay();
  }

  function renderTestimonials(list) {
    if (!track) return;

    if (!list || list.length === 0) {
      track.innerHTML = '<div class="testimonial-loading">No reviews yet. Be the first to share your experience!</div>';
      return;
    }

    track.innerHTML = list.map((t) => {
      const role = [t.position, t.company].filter(Boolean).join(', ');
      const avatar = t.avatar || (t.name || '??').slice(0, 2).toUpperCase();
      return (
        '<div class="testimonial-card">' +
          '<div class="testimonial-stars">' + starsHTML(t.rating || 5) + '</div>' +
          '<p class="testimonial-text">"' + t.text + '"</p>' +
          '<div class="testimonial-author">' +
            '<div class="author-avatar">' + avatar + '</div>' +
            '<div><strong>' + t.name + '</strong><span>' + role + '</span></div>' +
          '</div>' +
        '</div>'
      );
    }).join('');

    totalSlides = list.length;
    currentSlide = 0;
    track.style.transform = 'translateX(0)';

    if (dotsContainer) {
      dotsContainer.innerHTML = '';
      list.forEach(function (_, i) {
        const dot = document.createElement('button');
        dot.className = 'dot' + (i === 0 ? ' active' : '');
        dot.setAttribute('aria-label', 'Go to testimonial ' + (i + 1));
        dot.addEventListener('click', function () { goToSlide(i); });
        dotsContainer.appendChild(dot);
      });
    }

    // Bind prev/next
    if (prevBtn) {
      prevBtn.onclick = function () { goToSlide(currentSlide - 1); };
    }
    if (nextBtn) {
      nextBtn.onclick = function () { goToSlide(currentSlide + 1); };
    }

    // Pause on hover
    const slider = track.parentElement;
    if (slider) {
      slider.onmouseenter = function () { clearInterval(autoplayTimer); };
      slider.onmouseleave = function () { resetAutoplay(); };
    }

    resetAutoplay();
  }

  var FALLBACK_TESTIMONIALS = [
    { name: 'Sarah Kline', position: 'CEO', company: 'Aether Analytics', rating: 5, text: 'Webolite transformed our outdated site into a conversion machine. Traffic is up 340% and our sales pipeline has never looked better.', avatar: 'SK' },
    { name: 'Marcus Rivera', position: 'Founder', company: 'Pulse Labs', rating: 5, text: 'Working with Webolite felt like having an elite product team in-house. Their attention to detail and technical depth is unmatched.', avatar: 'MR' },
    { name: 'Elena Vargas', position: 'CMO', company: 'Lumina Fashion', rating: 5, text: 'They rebuilt our entire digital presence. Revenue grew 2.8x within six months of launch. Worth every penny.', avatar: 'EL' },
    { name: 'James Thornton', position: 'Director', company: 'Vertex Health', rating: 5, text: 'From strategy to launch, the process was seamless. The final product exceeded every expectation.', avatar: 'JT' }
  ];

  async function loadTestimonials() {
    if (!track) return;
    try {
      var res = await fetch('/api/testimonials');
      if (!res.ok) throw new Error('API ' + res.status);
      var data = await res.json();
      if (data.success && data.data && data.data.length) {
        renderTestimonials(data.data);
      } else {
        renderTestimonials(FALLBACK_TESTIMONIALS);
      }
    } catch (err) {
      console.error('Failed to load testimonials:', err);
      renderTestimonials(FALLBACK_TESTIMONIALS);
    }
  }

  loadTestimonials();

  /* ----- Review Form Submission ----- */
  function showReviewStatus(msg, type) {
    var el = document.getElementById('reviewStatus');
    if (!el) return;
    el.style.display = 'block';
    el.textContent = msg;
    if (type === 'ok') {
      el.style.background = 'rgba(16,185,129,0.15)';
      el.style.color = '#10B981';
      el.style.border = '1px solid rgba(16,185,129,0.3)';
    } else if (type === 'err') {
      el.style.background = 'rgba(244,63,94,0.12)';
      el.style.color = '#F43F5E';
      el.style.border = '1px solid rgba(244,63,94,0.25)';
    } else {
      el.style.background = 'rgba(124,111,255,0.12)';
      el.style.color = '#A59BFF';
      el.style.border = '1px solid rgba(124,111,255,0.25)';
    }
  }

  async function submitReview(e) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }

    var form = document.getElementById('reviewForm');
    var nameEl = document.getElementById('reviewName');
    var positionEl = document.getElementById('reviewPosition');
    var companyEl = document.getElementById('reviewCompany');
    var ratingEl = document.getElementById('reviewRating');
    var textEl = document.getElementById('reviewText');
    var btn = form ? form.querySelector('button[type="submit"]') : null;
    if (!form || !btn) return false;

    var original = btn.innerHTML;
    var name = nameEl ? nameEl.value.trim() : '';
    var text = textEl ? textEl.value.trim() : '';

    if (!name) {
      showReviewStatus('Please enter your name.', 'err');
      if (nameEl) nameEl.focus();
      return false;
    }
    if (!text || text.length < 10) {
      showReviewStatus('Please write at least 10 characters in your review.', 'err');
      if (textEl) textEl.focus();
      return false;
    }

    btn.innerHTML = 'Submitting...';
    btn.disabled = true;
    showReviewStatus('Sending your review...', 'info');

    try {
      var res = await fetch('/api/testimonials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name,
          position: positionEl ? positionEl.value.trim() : 'Client',
          company: companyEl ? companyEl.value.trim() : '',
          rating: ratingEl ? parseInt(ratingEl.value, 10) || 5 : 5,
          text: text,
        }),
      });

      var data = {};
      try { data = await res.json(); } catch (parseErr) { data = {}; }

      if (res.ok && data.success) {
        showReviewStatus('Thank you! Your review was submitted and is pending approval.', 'ok');
        btn.innerHTML = 'Submitted ✓';
        btn.style.background = '#10B981';
        form.reset();
        setTimeout(function () {
          btn.innerHTML = original;
          btn.disabled = false;
          btn.style.background = '';
        }, 4000);
      } else {
        showReviewStatus(data.error || 'Submit failed. Please try again.', 'err');
        btn.innerHTML = original;
        btn.disabled = false;
      }
    } catch (err) {
      console.error('Review submit error:', err);
      showReviewStatus('Server offline. Run: python3 server.py — then refresh this page.', 'err');
      btn.innerHTML = original;
      btn.disabled = false;
    }
    return false;
  }

  var reviewForm = document.getElementById('reviewForm');
  if (reviewForm) {
    reviewForm.addEventListener('submit', submitReview);
    // Also bind the button click as a backup
    var reviewBtn = reviewForm.querySelector('button[type="submit"]');
    if (reviewBtn) {
      reviewBtn.addEventListener('click', function (e) {
        // Let submit event handle it; this is a safety net if submit is blocked
      });
    }
  }
  // Expose for inline use if needed
  window.submitReview = submitReview;

  /* ----- Contact Form Validation ----- */
  const contactForm = document.getElementById('contactForm');

  if (contactForm) {
    contactForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      let valid = true;

      const name = contactForm.querySelector('#name');
      const email = contactForm.querySelector('#email');
      const company = contactForm.querySelector('#company');
      const budget = contactForm.querySelector('#budget');
      const message = contactForm.querySelector('#message');

      // Reset errors
      contactForm.querySelectorAll('.form-group').forEach((g) => {
        g.classList.remove('error');
        const msg = g.querySelector('.error-msg');
        if (msg) msg.textContent = '';
      });

      if (!name.value.trim()) {
        setError(name, 'Name is required');
        valid = false;
      }

      if (!email.value.trim()) {
        setError(email, 'Email is required');
        valid = false;
      } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) {
        setError(email, 'Please enter a valid email');
        valid = false;
      }

      if (!message.value.trim()) {
        setError(message, 'Please tell us about your project');
        valid = false;
      }

      if (!valid) return;

      const btn = contactForm.querySelector('button[type="submit"]');
      const original = btn.innerHTML;
      btn.innerHTML = 'Sending...';
      btn.disabled = true;

      try {
        const res = await fetch('/api/contact', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: name.value.trim(),
            email: email.value.trim(),
            company: company ? company.value.trim() : '',
            budget: budget ? budget.value : '',
            message: message.value.trim(),
          }),
        });

        const data = await res.json();

        if (res.ok && data.success) {
          btn.innerHTML = 'Message Sent ✓';
          btn.style.background = '#10B981';
          contactForm.reset();
          setTimeout(() => {
            btn.innerHTML = original;
            btn.disabled = false;
            btn.style.background = '';
          }, 3500);
        } else {
          throw new Error(data.error || 'Failed to send');
        }
      } catch (err) {
        btn.innerHTML = 'Try Again';
        btn.style.background = '#FF4D6D';
        btn.disabled = false;
        setTimeout(() => {
          btn.innerHTML = original;
          btn.style.background = '';
        }, 3000);
        console.error('Contact form error:', err);
      }
    });
  }

  function setError(input, message) {
    const group = input.closest('.form-group');
    group.classList.add('error');
    const msg = group.querySelector('.error-msg');
    if (msg) msg.textContent = message;
  }

  /* ----- Newsletter ----- */
  const newsletterForm = document.getElementById('newsletterForm');
  if (newsletterForm) {
    newsletterForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const input = newsletterForm.querySelector('input');
      const btn = newsletterForm.querySelector('button');
      const email = input.value.trim();

      if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        input.placeholder = 'Enter a valid email';
        input.value = '';
        return;
      }

      btn.disabled = true;

      try {
        const res = await fetch('/api/newsletter', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email }),
        });
        const data = await res.json();

        input.value = '';
        input.placeholder = data.success ? 'Subscribed! ✓' : (data.error || 'Error');
        setTimeout(() => {
          input.placeholder = 'Enter your email';
          btn.disabled = false;
        }, 2500);
      } catch {
        input.placeholder = 'Network error';
        setTimeout(() => {
          input.placeholder = 'Enter your email';
          btn.disabled = false;
        }, 2500);
      }
    });
  }

  /* ----- Button Ripple Effect ----- */
  document.querySelectorAll('.btn').forEach((btn) => {
    btn.addEventListener('mousemove', (e) => {
      const rect = btn.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      btn.style.setProperty('--x', x + '%');
      btn.style.setProperty('--y', y + '%');
    });
  });

  /* ----- Card Tilt Effect ----- */
  document.querySelectorAll('[data-tilt]').forEach((card) => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      const rotateX = ((y - centerY) / centerY) * -4;
      const rotateY = ((x - centerX) / centerX) * 4;
      card.style.transform = 'perspective(1000px) rotateX(' + rotateX + 'deg) rotateY(' + rotateY + 'deg) translateY(-6px)';
    });

    card.addEventListener('mouseleave', () => {
      card.style.transform = '';
    });
  });

  /* ----- Mouse Parallax on Hero Cards ----- */
  const heroCards = document.querySelectorAll('.glass-card');
  document.addEventListener('mousemove', (e) => {
    const cx = window.innerWidth / 2;
    const cy = window.innerHeight / 2;
    const dx = (e.clientX - cx) / cx;
    const dy = (e.clientY - cy) / cy;

    heroCards.forEach((card) => {
      const speed = parseFloat(card.getAttribute('data-speed')) || 0.02;
      card.style.transform = 'translate(' + dx * speed * 100 + 'px, ' + dy * speed * 100 + 'px)';
    });
  });

  /* ----- Smooth scroll for anchor links ----- */
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener('click', function (e) {
      const targetId = this.getAttribute('href');
      if (targetId === '#') return;
      const target = document.querySelector(targetId);
      if (target) {
        e.preventDefault();
        const offset = header.offsetHeight + 20;
        const top = target.getBoundingClientRect().top + window.scrollY - offset;
        window.scrollTo({ top, behavior: 'smooth' });
      }
    });
  });

  /* ----- Keyboard accessibility for FAQ ----- */
  faqItems.forEach((item) => {
    const question = item.querySelector('.faq-question');
    question.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        question.click();
      }
    });
  });


  /* ----- Visitor Tracking ----- */
  (function trackVisitors() {
    function getSessionId() {
      try {
        var id = sessionStorage.getItem('webolite_sid');
        if (!id) {
          id = 's_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
          sessionStorage.setItem('webolite_sid', id);
        }
        return id;
      } catch (e) {
        return 's_' + Math.random().toString(36).slice(2);
      }
    }

    function send(type) {
      var payload = {
        type: type || 'pageview',
        path: location.pathname + location.search,
        referrer: document.referrer || '',
        sessionId: getSessionId(),
      };
      try {
        fetch('/api/track', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          keepalive: true,
        }).catch(function () {});
      } catch (e) {}
    }

    send('pageview');
    // Heartbeat every 30s for live presence
    setInterval(function () { send('heartbeat'); }, 30000);
  })();


  /* ----- Custom cursor glow ----- */
  if (window.matchMedia('(pointer: fine)').matches) {
    var glow = document.createElement('div');
    glow.className = 'cursor-glow';
    document.body.appendChild(glow);
    var mx = 0, my = 0, cx = 0, cy = 0;
    document.addEventListener('mousemove', function (e) {
      mx = e.clientX;
      my = e.clientY;
    });
    (function loop() {
      cx += (mx - cx) * 0.18;
      cy += (my - cy) * 0.18;
      glow.style.left = cx + 'px';
      glow.style.top = cy + 'px';
      requestAnimationFrame(loop);
    })();
    document.querySelectorAll('a, button, .btn, .service-card, .portfolio-card, .filter-btn').forEach(function (el) {
      el.addEventListener('mouseenter', function () { glow.classList.add('active'); });
      el.addEventListener('mouseleave', function () { glow.classList.remove('active'); });
    });
  }

  /* ----- Magnetic buttons ----- */
  document.querySelectorAll('.btn-primary, .btn-lg').forEach(function (btn) {
    btn.addEventListener('mousemove', function (e) {
      var r = btn.getBoundingClientRect();
      var x = e.clientX - r.left - r.width / 2;
      var y = e.clientY - r.top - r.height / 2;
      btn.style.transform = 'translate(' + (x * 0.15) + 'px,' + (y * 0.2) + 'px)';
    });
    btn.addEventListener('mouseleave', function () {
      btn.style.transform = '';
    });
  });

  /* ----- Parallax hero video ----- */
  var heroVideo = document.querySelector('.hero-video');
  if (heroVideo) {
    window.addEventListener('scroll', function () {
      var y = window.scrollY;
      if (y < window.innerHeight) {
        heroVideo.style.transform = 'scale(1.08) translateY(' + (y * 0.25) + 'px)';
      }
    }, { passive: true });
  }

  /* ----- Init ----- */
  updateHeader();
  updateScrollProgress();
  updateBackToTop();
  updateActiveNav();

})();
