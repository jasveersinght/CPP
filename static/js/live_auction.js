// MATH AUCTION - Projector Large Screen Display Controller

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
  const projTimerBox = document.getElementById('proj-timer-box');
  const projTimerDigits = document.getElementById('proj-timer-digits');
  const projStartingBid = document.getElementById('proj-starting-bid');
  const projCurrentBid = document.getElementById('proj-current-bid');
  const projLeaderTeam = document.getElementById('proj-leader-team');

  let timerInterval = null;
  let lastWarningTick = 0;

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
    if (window.soundFX) window.soundFX.playBidSound();
  });

  socket.on('bid_update', (data) => {
    handleBidUpdate(data);
  });

  socket.on('auction_ended', (data) => {
    handleAuctionEnded(data);
  });

  function startTimer(endsAtIso, initialSeconds) {
    if (timerInterval) clearInterval(timerInterval);
    const endsAt = endsAtIso ? new Date(endsAtIso).getTime() : Date.now() + (initialSeconds * 1000);

    function tick() {
      const now = Date.now();
      const diffMs = endsAt - now;
      const secondsLeft = Math.max(0, Math.ceil(diffMs / 1000));

      if (projTimerDigits) {
        projTimerDigits.textContent = secondsLeft;
      }

      if (secondsLeft <= 3 && secondsLeft > 0) {
        projTimerBox.classList.add('warning');
        projMainCard.classList.add('ending-soon');
        if (window.soundFX && secondsLeft !== lastWarningTick) {
          lastWarningTick = secondsLeft;
          window.soundFX.playWarningTick();
        }
      } else {
        projTimerBox.classList.remove('warning');
        projMainCard.classList.remove('ending-soon');
      }

      if (secondsLeft <= 0) {
        clearInterval(timerInterval);
        projTimerDigits.textContent = '0';
        projTimerBox.classList.remove('warning');
      }
    }

    tick();
    timerInterval = setInterval(tick, 200);
  }

  function setLiveAuction(data) {
    projWinnerOverlay.style.display = 'none';
    projStandby.style.display = 'none';
    projActive.style.display = 'block';
    projMainCard.classList.add('active');

    projCategory.textContent = data.category || 'MATHEMATICS';
    projType.textContent = data.question_type || 'Numerical';
    projReward.textContent = `₹${parseFloat(data.reward).toFixed(2)}`;
    projQuestion.textContent = data.question_text || '';

    const imgContainer = document.getElementById('proj-image-container');
    const imgEl = document.getElementById('proj-question-image');
    if (data.question_image && imgContainer && imgEl) {
      imgEl.src = data.question_image;
      imgContainer.style.display = 'block';
    } else if (imgContainer) {
      imgContainer.style.display = 'none';
    }

    projStartingBid.textContent = `₹${parseFloat(data.starting_bid).toFixed(2)}`;
    projCurrentBid.textContent = `₹${parseFloat(data.current_bid).toFixed(2)}`;

    if (data.current_bidder_code) {
      projLeaderTeam.textContent = `${data.current_bidder_code} (${data.current_bidder_name || ''})`;
    } else {
      projLeaderTeam.textContent = 'Waiting For Opening Bid';
    }

    startTimer(data.ends_at_iso, data.time_remaining || 10);
  }

  function setStandby() {
    if (timerInterval) clearInterval(timerInterval);
    projStandby.style.display = 'block';
    projActive.style.display = 'none';
    projMainCard.classList.remove('active', 'ending-soon');
  }

  function handleBidUpdate(data) {
    projCurrentBid.textContent = `₹${parseFloat(data.current_bid).toFixed(2)}`;
    projLeaderTeam.textContent = `${data.current_bidder_code} (${data.current_bidder_name})`;

    // Scale animation on current bid
    projCurrentBid.style.transform = 'scale(1.2)';
    projCurrentBid.style.transition = 'transform 0.15s ease';
    setTimeout(() => projCurrentBid.style.transform = 'scale(1)', 150);

    if (window.soundFX) window.soundFX.playBidSound();
    startTimer(data.ends_at_iso, data.time_remaining || 10);
  }

  function handleAuctionEnded(data) {
    if (timerInterval) clearInterval(timerInterval);
    if (window.soundFX) window.soundFX.playGavel();

    if (data.has_winner) {
      projWinnerName.textContent = `TEAM ${data.winner_team_code}: ${data.winner_team_name}`;
      projWinningBidBanner.textContent = `Winning Hammer Price: ₹${parseFloat(data.winning_bid).toFixed(2)}`;
      projWinnerOverlay.style.display = 'flex';

      setTimeout(() => {
        projWinnerOverlay.style.display = 'none';
        setStandby();
      }, 5000);
    } else {
      setStandby();
    }
  }
});
