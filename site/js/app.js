// ==========================================================================
// JAGY Main Application Interactions & Simulator Engine
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
  // 1. Sticky Frosted Header on Scroll
  const navbar = document.getElementById('navbar');
  window.addEventListener('scroll', () => {
    if (window.scrollY > 40) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  });

  // 2. Interactive Channel Clipper Simulator
  const simInput = document.getElementById('sim-input');
  const simBtn = document.getElementById('sim-btn');
  const simCards = document.querySelectorAll('.sim-card');

  if (simBtn && simInput) {
    simBtn.addEventListener('click', () => {
      let channel = simInput.value.trim();
      if (!channel) channel = "@HubermanLab";

      simBtn.disabled = true;
      simBtn.innerHTML = `<span>Analyzing ${channel}...</span>`;

      // Stage 1: Ingestion
      activateStage(0, `Scanning ${channel}`, "Fetching 4K source video streams via yt-dlp...");

      setTimeout(() => {
        // Stage 2: AI Moment Detection
        activateStage(1, "Gemini AI Highlight Detection", "Identified 39s high-dopamine hook at 04:12 (Score: 98/100)");
      }, 1200);

      setTimeout(() => {
        // Stage 3: FFmpeg Crop & Publish
        activateStage(2, "9:16 Render & Hormozi Subs", "Smart face-tracked 1080x1920 short queued for YouTube & Instagram!");
        simBtn.disabled = false;
        simBtn.innerHTML = `<span>✓ Clip Generated!</span>`;
      }, 2400);
    });
  }

  function activateStage(index, title, status) {
    simCards.forEach((c, i) => {
      if (i === index) {
        c.classList.add('active');
        const titleEl = c.querySelector('.sim-card-title');
        const statusEl = c.querySelector('.sim-card-status');
        if (titleEl) titleEl.textContent = title;
        if (statusEl) statusEl.textContent = status;
      }
    });
  }

  // 3. FAQ Accordion Toggle
  const faqItems = document.querySelectorAll('.faq-item');
  faqItems.forEach(item => {
    const trigger = item.querySelector('.faq-trigger');
    if (trigger) {
      trigger.addEventListener('click', () => {
        const isOpen = item.classList.contains('active');
        faqItems.forEach(i => i.classList.remove('active'));
        if (!isOpen) {
          item.classList.add('active');
        }
      });
    }
  });
});
