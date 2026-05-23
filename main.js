(() => {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener('click', (event) => {
      const id = link.getAttribute('href').slice(1);
      if (!id) return;
      const target = document.getElementById(id);
      if (!target) return;
      event.preventDefault();
      target.scrollIntoView({
        behavior: reduceMotion ? 'auto' : 'smooth',
        block: 'start',
      });
    });
  });

  if (reduceMotion) return;

  const anchor = document.querySelector('.anchor-mass');
  const support = document.querySelector('.support-mass');
  const sliver = document.querySelector('.sliver-mark');
  if (!anchor) return;

  let ticking = false;
  const onScroll = () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      const y = window.scrollY;
      anchor.style.transform = `rotate(${-6 + y * 0.004}deg) translateY(${y * -0.04}px)`;
      if (support) support.style.transform = `rotate(${14 - y * 0.01}deg) translateY(${y * 0.06}px)`;
      if (sliver) sliver.style.transform = `rotate(${-22 + y * 0.02}deg) translateY(${y * -0.08}px)`;
      ticking = false;
    });
  };

  window.addEventListener('scroll', onScroll, { passive: true });
})();
