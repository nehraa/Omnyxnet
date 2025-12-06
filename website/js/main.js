/* ============================================
   Pangea Net - Interactive JavaScript
   ENHANCED with Rich Animations & Effects
   ============================================ */

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initScrollAnimations();
  initParallaxEffects();
  initNetworkCanvas();
  initCounterAnimations();
  initSmoothScrollLinks();
  initMagneticButtons();
  initCardEffects();
  initTextAnimations();
  initMouseFollower();
  initScrollProgress();
  initFloatingElements();
});

/* ============================================
   Navigation with Animations
   ============================================ */
function initNavigation() {
  const navToggle = document.querySelector('.nav-toggle');
  const navLinks = document.querySelector('.nav-links');
  const nav = document.querySelector('.nav');
  
  // Mobile menu toggle with animation
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
  
  // Navbar animation on scroll
  let lastScroll = 0;
  let ticking = false;
  
  window.addEventListener('scroll', () => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        const currentScroll = window.pageYOffset;
        
        if (nav) {
          if (currentScroll > 50) {
            nav.style.boxShadow = '0 4px 30px rgba(0, 0, 0, 0.1)';
            nav.style.backdropFilter = 'blur(20px)';
            nav.style.background = 'rgba(255, 251, 248, 0.98)';
          } else {
            nav.style.boxShadow = 'none';
            nav.style.backdropFilter = 'blur(10px)';
            nav.style.background = 'rgba(255, 251, 248, 0.95)';
          }
          
          // Hide/show on scroll direction
          if (currentScroll > lastScroll && currentScroll > 200) {
            nav.style.transform = 'translateY(-100%)';
          } else {
            nav.style.transform = 'translateY(0)';
          }
        }
        
        lastScroll = currentScroll;
        ticking = false;
      });
      ticking = true;
    }
  });
}

/* ============================================
   Enhanced Scroll Animations
   ============================================ */
function initScrollAnimations() {
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -80px 0px'
  };
  
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        
        // Trigger counter animation
        if (entry.target.hasAttribute('data-count')) {
          animateCounter(entry.target);
        }
        
        // Trigger line animation
        if (entry.target.classList.contains('animated-line')) {
          entry.target.style.width = '100%';
        }
        
        // Add bounce to icons
        if (entry.target.classList.contains('icon-bounce')) {
          entry.target.style.animation = 'bounce 0.8s cubic-bezier(0.4, 0, 0.2, 1)';
        }
      }
    });
  }, observerOptions);
  
  // Observe all animated elements
  const selectors = [
    '.scroll-animate',
    '.scroll-animate-left',
    '.scroll-animate-right',
    '.scroll-animate-scale',
    '.scroll-animate-rotate',
    '[data-count]',
    '.animated-line',
    '.icon-bounce'
  ];
  
  selectors.forEach(selector => {
    document.querySelectorAll(selector).forEach(el => {
      observer.observe(el);
    });
  });
}

/* ============================================
   Parallax Effects
   ============================================ */
function initParallaxEffects() {
  const parallaxElements = document.querySelectorAll('[data-parallax]');
  const floatingElements = document.querySelectorAll('.parallax-float');
  
  let ticking = false;
  
  window.addEventListener('scroll', () => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        const scrolled = window.pageYOffset;
        
        // Standard parallax
        parallaxElements.forEach(el => {
          const speed = el.dataset.parallax || 0.5;
          const yPos = -(scrolled * speed);
          el.style.transform = `translateY(${yPos}px)`;
        });
        
        // Floating elements with rotation
        floatingElements.forEach((el, index) => {
          const speed = 0.1 + (index * 0.05);
          const yPos = Math.sin(scrolled * 0.01 + index) * 20;
          const rotation = Math.sin(scrolled * 0.005 + index) * 5;
          el.style.transform = `translateY(${yPos}px) rotate(${rotation}deg)`;
        });
        
        ticking = false;
      });
      ticking = true;
    }
  });
}

/* ============================================
   Counter Animation with Glow
   ============================================ */
function initCounterAnimations() {
  // Counters are triggered by scroll observer
}

function animateCounter(element) {
  if (element.classList.contains('counted')) return;
  element.classList.add('counted');
  
  const target = parseFloat(element.getAttribute('data-count'));
  const duration = 2500;
  const startTime = performance.now();
  const startValue = 0;
  const isDecimal = target % 1 !== 0;
  const suffix = element.getAttribute('data-suffix') || '';
  
  // Add glow effect during counting
  element.style.textShadow = '0 0 20px rgba(32, 138, 141, 0.5)';
  
  function easeOutExpo(t) {
    return t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
  }
  
  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const easeProgress = easeOutExpo(progress);
    
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
      // Pulse effect at end
      element.style.animation = 'pulseGlow 0.5s ease-out';
      setTimeout(() => {
        element.style.textShadow = '';
        element.style.animation = '';
      }, 500);
    }
  }
  
  requestAnimationFrame(update);
}

/* ============================================
   Enhanced Network Canvas Animation
   ============================================ */
function initNetworkCanvas() {
  const canvas = document.getElementById('networkCanvas');
  if (!canvas) return;
  
  const ctx = canvas.getContext('2d');
  let animationId;
  let nodes = [];
  let connections = [];
  let mouseX = 0;
  let mouseY = 0;
  let time = 0;
  
  // Mouse tracking for interactive effect
  canvas.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    mouseX = e.clientX - rect.left;
    mouseY = e.clientY - rect.top;
  });
  
  function resizeCanvas() {
    canvas.width = canvas.offsetWidth * window.devicePixelRatio;
    canvas.height = canvas.offsetHeight * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    initNodes();
  }
  
  const MIN_NODE_SPACING = 60;
  function initNodes() {
    nodes = [];
    const nodeCount = Math.min(25, Math.floor(canvas.offsetWidth / MIN_NODE_SPACING));
    
    for (let i = 0; i < nodeCount; i++) {
      nodes.push({
        x: Math.random() * canvas.offsetWidth,
        y: Math.random() * canvas.offsetHeight,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        radius: Math.random() * 4 + 3,
        opacity: Math.random() * 0.5 + 0.5,
        pulsePhase: Math.random() * Math.PI * 2,
        orbitRadius: Math.random() * 30 + 10,
        orbitSpeed: (Math.random() - 0.5) * 0.02
      });
    }
  }
  
  function updateNodes() {
    time += 0.016;
    
    nodes.forEach(node => {
      // Base movement
      node.x += node.vx;
      node.y += node.vy;
      
      // Orbital motion
      const orbitX = Math.cos(time * node.orbitSpeed) * node.orbitRadius * 0.3;
      const orbitY = Math.sin(time * node.orbitSpeed) * node.orbitRadius * 0.3;
      
      // Mouse attraction
      const dx = mouseX - node.x;
      const dy = mouseY - node.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 150 && dist > 0) {
        const force = (150 - dist) / 150 * 0.02;
        node.vx += (dx / dist) * force;
        node.vy += (dy / dist) * force;
      }
      
      // Damping
      node.vx *= 0.99;
      node.vy *= 0.99;
      
      // Pulsing
      node.currentRadius = node.radius + Math.sin(time * 2 + node.pulsePhase) * 1;
      
      // Bounce off edges
      if (node.x < 0 || node.x > canvas.offsetWidth) node.vx *= -1;
      if (node.y < 0 || node.y > canvas.offsetHeight) node.vy *= -1;
      
      node.x = Math.max(0, Math.min(canvas.offsetWidth, node.x));
      node.y = Math.max(0, Math.min(canvas.offsetHeight, node.y));
    });
  }
  
  function findConnections() {
    connections = [];
    const maxDistance = 180;
    
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[i].x - nodes[j].x;
        const dy = nodes[i].y - nodes[j].y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance < maxDistance) {
          connections.push({
            from: nodes[i],
            to: nodes[j],
            opacity: 1 - (distance / maxDistance),
            distance: distance
          });
        }
      }
    }
  }
  
  function draw() {
    ctx.clearRect(0, 0, canvas.offsetWidth, canvas.offsetHeight);
    
    // Draw connections with gradient
    connections.forEach(conn => {
      const gradient = ctx.createLinearGradient(
        conn.from.x, conn.from.y, conn.to.x, conn.to.y
      );
      gradient.addColorStop(0, `rgba(32, 138, 141, ${conn.opacity * 0.4})`);
      gradient.addColorStop(0.5, `rgba(50, 184, 198, ${conn.opacity * 0.6})`);
      gradient.addColorStop(1, `rgba(32, 138, 141, ${conn.opacity * 0.4})`);
      
      ctx.beginPath();
      ctx.moveTo(conn.from.x, conn.from.y);
      ctx.lineTo(conn.to.x, conn.to.y);
      ctx.strokeStyle = gradient;
      ctx.lineWidth = conn.opacity * 2;
      ctx.stroke();
      
      // Animated data packet
      if (conn.opacity > 0.5 && Math.random() < 0.01) {
        const t = (time * 0.5) % 1;
        const packetX = conn.from.x + (conn.to.x - conn.from.x) * t;
        const packetY = conn.from.y + (conn.to.y - conn.from.y) * t;
        
        ctx.beginPath();
        ctx.arc(packetX, packetY, 3, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(50, 184, 198, 0.8)';
        ctx.fill();
      }
    });
    
    // Draw nodes with enhanced glow
    nodes.forEach(node => {
      // Outer glow
      const gradient = ctx.createRadialGradient(
        node.x, node.y, 0,
        node.x, node.y, node.currentRadius * 4
      );
      gradient.addColorStop(0, `rgba(32, 138, 141, ${node.opacity * 0.8})`);
      gradient.addColorStop(0.5, `rgba(50, 184, 198, ${node.opacity * 0.3})`);
      gradient.addColorStop(1, 'rgba(32, 138, 141, 0)');
      
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.currentRadius * 4, 0, Math.PI * 2);
      ctx.fillStyle = gradient;
      ctx.fill();
      
      // Core with ring
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.currentRadius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(50, 184, 198, ${node.opacity})`;
      ctx.fill();
      
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.currentRadius + 2, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(32, 138, 141, ${node.opacity * 0.5})`;
      ctx.lineWidth = 1;
      ctx.stroke();
    });
  }
  
  function animate() {
    updateNodes();
    findConnections();
    draw();
    animationId = requestAnimationFrame(animate);
  }
  
  resizeCanvas();
  animate();
  
  window.addEventListener('resize', debounce(resizeCanvas, 200));
  
  window.addEventListener('beforeunload', () => {
    cancelAnimationFrame(animationId);
  });
}

/* ============================================
   Magnetic Buttons Effect
   ============================================ */
function initMagneticButtons() {
  document.querySelectorAll('.btn, .nav-cta').forEach(btn => {
    btn.addEventListener('mousemove', function(e) {
      const rect = this.getBoundingClientRect();
      const x = e.clientX - rect.left - rect.width / 2;
      const y = e.clientY - rect.top - rect.height / 2;
      
      this.style.transform = `translate(${x * 0.2}px, ${y * 0.2}px)`;
    });
    
    btn.addEventListener('mouseleave', function() {
      this.style.transform = '';
      this.style.transition = 'transform 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
    });
    
    btn.addEventListener('mouseenter', function() {
      this.style.transition = 'transform 0.15s cubic-bezier(0.4, 0, 0.2, 1)';
    });
  });
}

/* ============================================
   Enhanced Card Effects
   ============================================ */
function initCardEffects() {
  document.querySelectorAll('.card').forEach(card => {
    // 3D tilt effect
    card.addEventListener('mousemove', function(e) {
      const rect = this.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      
      const tiltX = (y - centerY) / 15;
      const tiltY = (centerX - x) / 15;
      
      this.style.transform = `
        translateY(-12px) 
        perspective(1000px) 
        rotateX(${tiltX}deg) 
        rotateY(${tiltY}deg)
        scale(1.02)
      `;
      this.style.boxShadow = `
        ${-tiltY * 2}px ${tiltX * 2}px 30px rgba(32, 138, 141, 0.15),
        0 20px 40px rgba(0, 0, 0, 0.1)
      `;
      
      // Shine effect
      const shine = this.querySelector('.card-shine') || createShine(this);
      shine.style.background = `
        radial-gradient(
          circle at ${x}px ${y}px,
          rgba(255, 255, 255, 0.2) 0%,
          transparent 50%
        )
      `;
    });
    
    card.addEventListener('mouseleave', function() {
      this.style.transform = '';
      this.style.boxShadow = '';
      const shine = this.querySelector('.card-shine');
      if (shine) shine.style.background = '';
    });
  });
  
  function createShine(card) {
    const shine = document.createElement('div');
    shine.className = 'card-shine';
    shine.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      pointer-events: none;
      border-radius: inherit;
    `;
    card.style.position = 'relative';
    card.style.overflow = 'hidden';
    card.appendChild(shine);
    return shine;
  }
}

/* ============================================
   Text Animations
   ============================================ */
function initTextAnimations() {
  // Skip hero title letter animation - it breaks HTML
  // Just add gradient animation to highlights
  
  // Gradient text animation for highlights
  document.querySelectorAll('.highlight, .gradient-text').forEach(el => {
    el.style.backgroundSize = '200% 200%';
    el.style.animation = 'gradientShift 4s ease infinite';
  });
}

/* ============================================
   Custom Cursor / Mouse Follower
   ============================================ */
function initMouseFollower() {
  // Only on desktop
  if (window.matchMedia('(pointer: fine)').matches) {
    const follower = document.createElement('div');
    follower.className = 'mouse-follower';
    follower.style.cssText = `
      position: fixed;
      width: 20px;
      height: 20px;
      border: 2px solid rgba(32, 138, 141, 0.5);
      border-radius: 50%;
      pointer-events: none;
      z-index: 9999;
      transition: transform 0.15s ease-out, width 0.2s, height 0.2s, border-color 0.2s;
      transform: translate(-50%, -50%);
    `;
    document.body.appendChild(follower);
    
    let mouseX = 0, mouseY = 0;
    let followerX = 0, followerY = 0;
    
    document.addEventListener('mousemove', (e) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
    });
    
    function animateFollower() {
      followerX += (mouseX - followerX) * 0.15;
      followerY += (mouseY - followerY) * 0.15;
      
      follower.style.left = followerX + 'px';
      follower.style.top = followerY + 'px';
      
      requestAnimationFrame(animateFollower);
    }
    animateFollower();
    
    // Expand on hover over links/buttons
    document.querySelectorAll('a, button, .card').forEach(el => {
      el.addEventListener('mouseenter', () => {
        follower.style.width = '40px';
        follower.style.height = '40px';
        follower.style.borderColor = 'rgba(32, 138, 141, 0.8)';
        follower.style.background = 'rgba(32, 138, 141, 0.1)';
      });
      el.addEventListener('mouseleave', () => {
        follower.style.width = '20px';
        follower.style.height = '20px';
        follower.style.borderColor = 'rgba(32, 138, 141, 0.5)';
        follower.style.background = 'transparent';
      });
    });
  }
}

/* ============================================
   Scroll Progress Indicator
   ============================================ */
function initScrollProgress() {
  const progress = document.createElement('div');
  progress.className = 'scroll-progress';
  progress.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    height: 3px;
    background: linear-gradient(90deg, #208A8D, #32B8C6);
    z-index: 10001;
    transition: width 0.1s ease-out;
    box-shadow: 0 0 10px rgba(32, 138, 141, 0.5);
  `;
  document.body.appendChild(progress);
  
  window.addEventListener('scroll', () => {
    const windowHeight = document.documentElement.scrollHeight - window.innerHeight;
    const scrolled = (window.pageYOffset / windowHeight) * 100;
    progress.style.width = scrolled + '%';
  });
}

/* ============================================
   Floating Decorative Elements
   ============================================ */
function initFloatingElements() {
  // Add floating orbs to hero section
  const hero = document.querySelector('.hero');
  if (hero) {
    for (let i = 0; i < 3; i++) {
      const orb = document.createElement('div');
      orb.className = 'glow-orb glow-orb-' + (i + 1);
      orb.style.cssText = `
        position: absolute;
        border-radius: 50%;
        filter: blur(60px);
        pointer-events: none;
        animation: floatSlow ${8 + i * 2}s ease-in-out infinite, pulseGlow ${4 + i}s ease-in-out infinite;
        animation-delay: ${i * -3}s;
      `;
      
      if (i === 0) {
        orb.style.width = '400px';
        orb.style.height = '400px';
        orb.style.background = 'rgba(32, 138, 141, 0.12)';
        orb.style.top = '10%';
        orb.style.right = '-10%';
      } else if (i === 1) {
        orb.style.width = '300px';
        orb.style.height = '300px';
        orb.style.background = 'rgba(50, 184, 198, 0.08)';
        orb.style.bottom = '20%';
        orb.style.left = '-5%';
      } else {
        orb.style.width = '250px';
        orb.style.height = '250px';
        orb.style.background = 'rgba(32, 138, 141, 0.06)';
        orb.style.top = '50%';
        orb.style.left = '30%';
      }
      
      hero.appendChild(orb);
    }
  }
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
    
    const formData = new FormData(this);
    const data = Object.fromEntries(formData);
    
    const successMsg = document.createElement('div');
    successMsg.className = 'survey-success';
    successMsg.innerHTML = `
      <div class="success-icon">✓</div>
      <h3>Thank you for your feedback!</h3>
      <p>Your responses help shape the future of Pangea Net.</p>
    `;
    
    this.parentNode.replaceChild(successMsg, this);
    
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

/* ============================================
   Letter Animation Styles (injected)
   ============================================ */
const letterStyles = document.createElement('style');
letterStyles.textContent = `
  .letter-animate {
    display: inline-block;
    animation: fadeInUp 0.5s cubic-bezier(0.4, 0, 0.2, 1) forwards;
    opacity: 0;
  }
  
  @keyframes floatSlow {
    0%, 100% { transform: translateY(0) scale(1); }
    50% { transform: translateY(-30px) scale(1.05); }
  }
  
  @keyframes pulseGlow {
    0%, 100% { opacity: 0.6; }
    50% { opacity: 1; }
  }
`;
document.head.appendChild(letterStyles);
