/* ============================================
   Pangea Net - Interactive JavaScript
   Smooth Animations & Micro-interactions
   ============================================ */

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initScrollAnimations();
  initNetworkCanvas();
  initCounterAnimations();
  initSmoothScrollLinks();
});

/* ============================================
   Navigation
   ============================================ */
function initNavigation() {
  const navToggle = document.querySelector('.nav-toggle');
  const navLinks = document.querySelector('.nav-links');
  const nav = document.querySelector('.nav');
  
  // Mobile menu toggle
  if (navToggle && navLinks) {
    navToggle.addEventListener('click', () => {
      navLinks.classList.toggle('active');
      navToggle.classList.toggle('active');
    });
    
    // Close menu when clicking a link
    navLinks.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        navLinks.classList.remove('active');
        navToggle.classList.remove('active');
      });
    });
  }
  
  // Navbar background on scroll
  let lastScroll = 0;
  window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;
    
    if (nav) {
      if (currentScroll > 50) {
        nav.style.boxShadow = '0 2px 20px rgba(0, 0, 0, 0.1)';
      } else {
        nav.style.boxShadow = 'none';
      }
    }
    
    lastScroll = currentScroll;
  });
}

/* ============================================
   Scroll Animations (Intersection Observer)
   ============================================ */
function initScrollAnimations() {
  const observerOptions = {
    threshold: 0.15,
    rootMargin: '0px 0px -50px 0px'
  };
  
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        
        // If it's a counter, start counting
        if (entry.target.hasAttribute('data-count')) {
          animateCounter(entry.target);
        }
      }
    });
  }, observerOptions);
  
  // Observe all elements with scroll-animate class
  document.querySelectorAll('.scroll-animate').forEach(el => {
    observer.observe(el);
  });
  
  // Observe counters
  document.querySelectorAll('[data-count]').forEach(el => {
    observer.observe(el);
  });
}

/* ============================================
   Counter Animation
   ============================================ */
function initCounterAnimations() {
  // Counters will be triggered by scroll observer
}

function animateCounter(element) {
  if (element.classList.contains('counted')) return;
  element.classList.add('counted');
  
  const target = parseFloat(element.getAttribute('data-count'));
  const duration = 2000;
  const startTime = performance.now();
  const startValue = 0;
  const isDecimal = target % 1 !== 0;
  const suffix = element.getAttribute('data-suffix') || '';
  
  function easeOutCubic(t) {
    return 1 - Math.pow(1 - t, 3);
  }
  
  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const easeProgress = easeOutCubic(progress);
    
    let currentValue = startValue + (target - startValue) * easeProgress;
    
    if (isDecimal) {
      currentValue = currentValue.toFixed(2);
    } else {
      currentValue = Math.floor(currentValue);
    }
    
    element.textContent = currentValue + suffix;
    
    if (progress < 1) {
      requestAnimationFrame(update);
    } else {
      element.textContent = target + suffix;
    }
  }
  
  requestAnimationFrame(update);
}

/* ============================================
   Network Canvas Animation
   ============================================ */
function initNetworkCanvas() {
  const canvas = document.getElementById('networkCanvas');
  if (!canvas) return;
  
  const ctx = canvas.getContext('2d');
  let animationId;
  let nodes = [];
  let connections = [];
  
  // Set canvas size
  function resizeCanvas() {
    canvas.width = canvas.offsetWidth * window.devicePixelRatio;
    canvas.height = canvas.offsetHeight * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    initNodes();
  }
  
  // Initialize nodes
  const MIN_NODE_SPACING = 80;
  function initNodes() {
    nodes = [];
    const nodeCount = Math.min(15, Math.floor(canvas.offsetWidth / MIN_NODE_SPACING));
    
    for (let i = 0; i < nodeCount; i++) {
      nodes.push({
        x: Math.random() * canvas.offsetWidth,
        y: Math.random() * canvas.offsetHeight,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        radius: Math.random() * 3 + 4,
        opacity: Math.random() * 0.5 + 0.5
      });
    }
  }
  
  // Update node positions
  function updateNodes() {
    nodes.forEach(node => {
      node.x += node.vx;
      node.y += node.vy;
      
      // Bounce off edges
      if (node.x < 0 || node.x > canvas.offsetWidth) node.vx *= -1;
      if (node.y < 0 || node.y > canvas.offsetHeight) node.vy *= -1;
      
      // Keep in bounds
      node.x = Math.max(0, Math.min(canvas.offsetWidth, node.x));
      node.y = Math.max(0, Math.min(canvas.offsetHeight, node.y));
    });
  }
  
  // Find connections between nearby nodes
  function findConnections() {
    connections = [];
    const maxDistance = 150;
    
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[i].x - nodes[j].x;
        const dy = nodes[i].y - nodes[j].y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance < maxDistance) {
          connections.push({
            from: nodes[i],
            to: nodes[j],
            opacity: 1 - (distance / maxDistance)
          });
        }
      }
    }
  }
  
  // Draw everything
  function draw() {
    ctx.clearRect(0, 0, canvas.offsetWidth, canvas.offsetHeight);
    
    // Draw connections
    connections.forEach(conn => {
      ctx.beginPath();
      ctx.moveTo(conn.from.x, conn.from.y);
      ctx.lineTo(conn.to.x, conn.to.y);
      ctx.strokeStyle = `rgba(32, 138, 141, ${conn.opacity * 0.3})`;
      ctx.lineWidth = 1;
      ctx.stroke();
    });
    
    // Draw nodes
    nodes.forEach(node => {
      // Glow effect
      const gradient = ctx.createRadialGradient(
        node.x, node.y, 0,
        node.x, node.y, node.radius * 2
      );
      gradient.addColorStop(0, `rgba(32, 138, 141, ${node.opacity})`);
      gradient.addColorStop(1, 'rgba(32, 138, 141, 0)');
      
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.radius * 2, 0, Math.PI * 2);
      ctx.fillStyle = gradient;
      ctx.fill();
      
      // Core
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(32, 138, 141, ${node.opacity})`;
      ctx.fill();
    });
  }
  
  // Animation loop
  function animate() {
    updateNodes();
    findConnections();
    draw();
    animationId = requestAnimationFrame(animate);
  }
  
  // Start animation
  resizeCanvas();
  animate();
  
  // Handle resize
  window.addEventListener('resize', () => {
    resizeCanvas();
  });
  
  // Cleanup on page leave
  window.addEventListener('beforeunload', () => {
    cancelAnimationFrame(animationId);
  });
}

/* ============================================
   Smooth Scroll for Anchor Links
   ============================================ */
function initSmoothScrollLinks() {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const targetId = this.getAttribute('href');
      if (targetId === '#') return;
      
      const target = document.querySelector(targetId);
      if (target) {
        e.preventDefault();
        const navHeight = document.querySelector('.nav')?.offsetHeight || 0;
        const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - navHeight - 20;
        
        window.scrollTo({
          top: targetPosition,
          behavior: 'smooth'
        });
      }
    });
  });
}

/* ============================================
   Button Hover Effects
   ============================================ */
document.querySelectorAll('.btn').forEach(btn => {
  btn.addEventListener('mouseenter', function(e) {
    const rect = this.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    this.style.setProperty('--mouse-x', x + 'px');
    this.style.setProperty('--mouse-y', y + 'px');
  });
});

/* ============================================
   Card Tilt Effect (Subtle)
   ============================================ */
document.querySelectorAll('.card').forEach(card => {
  card.addEventListener('mousemove', function(e) {
    const rect = this.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    
    const tiltX = (y - centerY) / 20;
    const tiltY = (centerX - x) / 20;
    
    this.style.transform = `translateY(-8px) perspective(1000px) rotateX(${tiltX}deg) rotateY(${tiltY}deg)`;
  });
  
  card.addEventListener('mouseleave', function() {
    this.style.transform = '';
  });
});

/* ============================================
   Typing Effect for Terminal
   ============================================ */
function typeWriter(element, text, speed = 30) {
  let index = 0;
  element.textContent = '';
  
  function type() {
    if (index < text.length) {
      element.textContent += text.charAt(index);
      index++;
      setTimeout(type, speed);
    }
  }
  
  type();
}

/* ============================================
   Survey Form Handling
   ============================================ */
function initSurvey() {
  const surveyForm = document.getElementById('surveyForm');
  if (!surveyForm) return;
  
  surveyForm.addEventListener('submit', function(e) {
    e.preventDefault();
    
    // Collect form data
    const formData = new FormData(this);
    const data = Object.fromEntries(formData);
    
    // Show success message
    const successMsg = document.createElement('div');
    successMsg.className = 'survey-success';
    successMsg.innerHTML = `
      <div class="success-icon">✓</div>
      <h3>Thank you for your feedback!</h3>
      <p>Your responses help shape the future of Pangea Net.</p>
    `;
    
    this.parentNode.replaceChild(successMsg, this);
    
    // Animate success message
    successMsg.style.opacity = '0';
    successMsg.style.transform = 'scale(0.9)';
    requestAnimationFrame(() => {
      successMsg.style.transition = 'all 0.5s ease-out';
      successMsg.style.opacity = '1';
      successMsg.style.transform = 'scale(1)';
    });
  });
}

/* ============================================
   Performance: Debounce & Throttle
   ============================================ */
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

function throttle(func, limit) {
  let inThrottle;
  return function(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

// Throttle scroll events
window.addEventListener('scroll', throttle(() => {
  // Any scroll-dependent logic here
}, 100));
