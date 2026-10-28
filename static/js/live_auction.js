// MATH AUCTION - Projector Large Screen Display Controller
// Supports 10s Question Reading Time and 30s Bid Time

document.addEventListener('DOMContentLoaded', () => {
  const projMainCard = document.getElementById('proj-main-card');
  const projStandby = document.getElementById('proj-standby');
  const projActive = document.getElementById('proj-active');
  const projWinnerOverlay = document.getElementById('proj-winner-overlay');
  const projWinnerName = document.getElementById('proj-winner-name');
  const projWinningBidBanner = document.getElementById('proj-winning-bid-banner');

  const projCategory = document.getElementById('proj-category');
  const projType = document.getElementById('proj-type');
  const projReward = document.getElementById('proj-reward');
  const projQuestion = document.getElementById('proj-question');
  const projPhaseBanner = document.getElementById('proj-phase-banner');
  const projPhaseIcon = document.getElementById('proj-phase-icon');
  const projPhaseText = document.getElementById('proj-phase-text');
  const projTimerBox = document.getElementById('proj-timer-box');
  const projTimerDigits = document.getElementById('proj-timer-digits');
  const projTimerLabel = document.getElementById('proj-timer-label');
  const projStartingBid = document.getElementById('proj-starting-bid');
  const projCurrentBid = document.getElementById('proj-current-bid');
  const projLeaderTeam = document.getElementById('proj-leader-team');

  let timerInterval = null;
  let lastWarningTick = 0;
  let currentAuctionPhase = 'BIDDING';

  const socket = io({
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 1000
  });

  socket.on('connect', () => {
    console.log('[Projector] Connected to auction socket.');
    socket.emit('request_sync');
  });

  socket.on('sync_state', (data) => {
    if (data.active_auction) {
      setLiveAuction(data.active_auction);
    } else {
      setStandby();
    }
  });

  socket.on('auction_started', (data) => {
    setLiveAuction(data);
    try {
      if (window.soundFX) window.soundFX.playBidSound();
    } catch (e) {}
  });

  socket.on('bid_update', (data) => {
    handleBidUpdate(data);
  });

  socket.on('auction_ended', (data) => {
    handleAuctionEnded(data);
  });

  function startTimer(biddingStartsAtIso, endsAtIso, initialSeconds) {
    if (timerInterval) clearInterval(timerInterval);
    const biddingStartsAtMs = biddingStartsAtIso ? new Date(biddingStartsAtIso).getTime() : 0;
    const endsAtMs = endsAtIso ? new Date(endsAtIso).getTime() : Date.now() + ((initialSeconds || 40) * 1000);

    function tick() {
      const now = Date.now();
      const diffMs = endsAtMs - now;
      const totalSecLeft = Math.max(0, Math.ceil(diffMs / 1000));

      // Always show total 40s countdown
      if (projTimerDigits) projTimerDigits.textContent = totalSecLeft;
      if (projTimerLabel) projTimerLabel.textContent = 'Seconds';

      // Check Question Reading Phase (10s: from 40s down to 30s)
      if (biddingStartsAtMs && now < biddingStartsAtMs) {
        const readingMsLeft = biddingStartsAtMs - now;
        const readingSecLeft = Math.max(0, Math.ceil(readingMsLeft / 1000));
        currentAuctionPhase = 'READING';

        if (projPhaseBanner) {
          projPhaseBanner.style.display = 'block';
          projPhaseBanner.className = 'phase-banner-reading';
          if (projPhaseIcon) projPhaseIcon.textContent = '📖';
          if (projPhaseText) projPhaseText.textContent = 'QUESTION READING TIME (Bidding opens at 30s)';
        }

        if (projTimerBox) {
          projTimerBox.classList.add('reading-phase');
          projTimerBox.classList.remove('warning');
        }
        if (projMainCard) projMainCard.classList.remove('ending-soon');

        if (projLeaderTeam) {
          projLeaderTeam.textContent = `Bidding opens in ${readingSecLeft}s`;
          projLeaderTeam.style.color = 'var(--accent-cyan)';
        }
        return;
      }

      // Transition to Bidding Phase (30s)
      if (currentAuctionPhase === 'READING') {
        currentAuctionPhase = 'BIDDING';
        try {
          if (window.soundFX) window.soundFX.playBiddingOpenSound();
        } catch (e) {}
      }

      if (projPhaseBanner) {
        projPhaseBanner.style.display = 'block';
        projPhaseBanner.className = 'phase-banner-bidding';
        if (projPhaseIcon) projPhaseIcon.textContent = '🔥';
        if (projPhaseText) projPhaseText.textContent = 'BID TIME (30s) — LIVE BIDDING OPEN';
      }

      if (projTimerBox) {
        projTimerBox.classList.remove('reading-phase');
      }

      if (projTimerBox) {
        projTimerBox.classList.remove('reading-phase');
      }

      if (secondsLeft <= 3 && secondsLeft > 0) {
        if (projTimerBox) projTimerBox.classList.add('warning');
        if (projMainCard) projMainCard.classList.add('ending-soon');
        if (window.soundFX && secondsLeft !== lastWarningTick) {
          lastWarningTick = secondsLeft;
          try { window.soundFX.playWarningTick(); } catch (e) {}
        }
      } else {
        if (projTimerBox) projTimerBox.classList.remove('warning');
        if (projMainCard) projMainCard.classList.remove('ending-soon');
      }

      if (secondsLeft <= 0) {
        clearInterval(timerInterval);
        if (projTimerDigits) projTimerDigits.textContent = '0';
        if (projTimerBox) projTimerBox.classList.remove('warning');
      }
    }

    tick();
    timerInterval = setInterval(tick, 200);
  }

  function setLiveAuction(data) {
    if (projWinnerOverlay) projWinnerOverlay.style.display = 'none';
    if (projStandby) projStandby.style.display = 'none';
    if (projActive) projActive.style.display = 'block';
    if (projMainCard) projMainCard.classList.add('active');

    if (projCategory) projCategory.textContent = data.category || 'MATHEMATICS';
    if (projType) projType.textContent = data.question_type || 'Numerical';
    if (projReward) projReward.textContent = `₹${parseFloat(data.reward).toFixed(2)}`;
    if (projQuestion) projQuestion.textContent = data.question_text || '';

    const imgContainer = document.getElementById('proj-image-container');
    const imgEl = document.getElementById('proj-question-image');
    if (data.question_image && imgContainer && imgEl) {
      imgEl.src = data.question_image;
      imgContainer.style.display = 'block';
    } else if (imgContainer) {
      imgContainer.style.display = 'none';
    }

    if (projStartingBid) projStartingBid.textContent = `₹${parseFloat(data.starting_bid).toFixed(2)}`;
    if (projCurrentBid) projCurrentBid.textContent = `₹${parseFloat(data.current_bid).toFixed(2)}`;

    if (data.current_bidder_code) {
      if (projLeaderTeam) projLeaderTeam.textContent = `${data.current_bidder_code} (${data.current_bidder_name || ''})`;
    } else {
      if (projLeaderTeam) projLeaderTeam.textContent = 'Waiting For Opening Bid';
    }

    startTimer(data.bidding_starts_at_iso, data.ends_at_iso, data.time_remaining || 30);
  }

  function setStandby() {
    currentAuctionPhase = 'BIDDING';
    if (timerInterval) clearInterval(timerInterval);
    if (projStandby) projStandby.style.display = 'block';
    if (projActive) projActive.style.display = 'none';
    if (projPhaseBanner) projPhaseBanner.style.display = 'none';
    if (projMainCard) projMainCard.classList.remove('active', 'ending-soon');
  }

  function handleBidUpdate(data) {
    if (projCurrentBid) projCurrentBid.textContent = `₹${parseFloat(data.current_bid).toFixed(2)}`;
    if (projLeaderTeam) {
      projLeaderTeam.textContent = `${data.current_bidder_code} (${data.current_bidder_name})`;
      projLeaderTeam.style.color = '#22d3ee';
    }

    // Scale animation on current bid
    if (projCurrentBid) {
      projCurrentBid.style.transform = 'scale(1.2)';
      projCurrentBid.style.transition = 'transform 0.15s ease';
      setTimeout(() => {
        if (projCurrentBid) projCurrentBid.style.transform = 'scale(1)';
      }, 150);
    }

    try {
      if (window.soundFX) window.soundFX.playBidSound();
    } catch (e) {}

    // Bidding phase reset to 30s
    startTimer(null, data.ends_at_iso, data.time_remaining || 30);
  }

  function handleAuctionEnded(data) {
    if (timerInterval) clearInterval(timerInterval);
    try {
      if (window.soundFX) window.soundFX.playGavel();
    } catch (e) {}

    if (data.has_winner) {
      if (projWinnerName) projWinnerName.textContent = `TEAM ${data.winner_team_code}: ${data.winner_team_name}`;
      if (projWinningBidBanner) projWinningBidBanner.textContent = `Winning Hammer Price: ₹${parseFloat(data.winning_bid).toFixed(2)}`;
      if (projWinnerOverlay) projWinnerOverlay.style.display = 'flex';

      setTimeout(() => {
        if (projWinnerOverlay) projWinnerOverlay.style.display = 'none';
        setStandby();
      }, 5000);
    } else {
      setStandby();
    }
  }
});
