// MATH AUCTION - Team Dashboard Controller
// Server-Authoritative Real-Time Auction & 5-Question Repository Engine

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements - Navigation & Stats
  const navBalancePill = document.getElementById('nav-balance-pill');
  const navTeamBalance = document.getElementById('nav-team-balance');
  const statBalance = document.getElementById('stat-balance');
  const statRank = document.getElementById('stat-rank');
  const statCompleted = document.getElementById('stat-completed');
  const statWon = document.getElementById('stat-won');
  const displayWonCount = document.getElementById('display-won-count');
  const displaySolvedCount = document.getElementById('display-solved-count');

  // DOM Elements - Active Auction Hero
  const auctionContainer = document.getElementById('auction-container');
  const auctionEmptyState = document.getElementById('auction-empty-state');
  const auctionActiveState = document.getElementById('auction-active-state');
  const auctionCategory = document.getElementById('auction-category');
  const auctionTypeBadge = document.getElementById('auction-type-badge');
  const auctionReward = document.getElementById('auction-reward');
  const auctionSummaryText = document.getElementById('auction-summary-text');
  const auctionImageContainer = document.getElementById('auction-image-container');
  const auctionQuestionImage = document.getElementById('auction-question-image');
  const auctionStartingBid = document.getElementById('auction-starting-bid');
  const auctionCurrentBid = document.getElementById('auction-current-bid');
  const auctionHighestBidder = document.getElementById('auction-highest-bidder');
  const auctionPhaseBanner = document.getElementById('auction-phase-banner');
  const auctionPhaseIcon = document.getElementById('auction-phase-icon');
  const auctionPhaseText = document.getElementById('auction-phase-text');
  const auctionTimerBox = document.getElementById('auction-timer-box');
  const auctionTimerDigits = document.getElementById('auction-timer-digits');
  const auctionTimerLabel = document.getElementById('auction-timer-label');
  const leaderNotice = document.getElementById('leader-notice');
  const btnPlaceBid = document.getElementById('btn-place-bid');
  const btnBidAmount = document.getElementById('btn-bid-amount');
  const bidWarningMsg = document.getElementById('bid-warning-msg');

  // DOM Elements - Won Questions Repository
  const wonQuestionsPanel = document.getElementById('won-questions-panel');
  const repoCount = document.getElementById('repo-count');
  const wonEmptyMsg = document.getElementById('won-empty-msg');
  const wonQuestionsContainer = document.getElementById('won-questions-container');

  // DOM Elements - Leaderboard & Ledger
  const leaderboardBody = document.getElementById('leaderboard-body');
  const transactionsBody = document.getElementById('transactions-body');
  const btnRefreshLedger = document.getElementById('btn-refresh-ledger');

  // Application State
  let activeAuction = null;
  let timerInterval = null;
  let clientBalance = (typeof window.INITIAL_BALANCE === 'number') ? window.INITIAL_BALANCE : 10000.0;
  let questionsWon = 0;
  let questionsCompleted = 0;
  let isDisqualified = (typeof window.IS_DISQUALIFIED === 'boolean') ? window.IS_DISQUALIFIED : false;
  let lastWarningTick = 0;
  let lastViolationTs = 0;
  let currentAuctionPhase = 'BIDDING'; // 'READING' or 'BIDDING'

  // Initialize balance display cleanly
  updateBalanceDisplay(clientBalance);

  // If already disqualified on page load/refresh, lock the dashboard immediately
  if (isDisqualified) {
    if (btnPlaceBid) btnPlaceBid.disabled = true;
    if (bidWarningMsg) {
      bidWarningMsg.textContent = 'DISQUALIFIED — You may not participate further.';
      bidWarningMsg.style.color = '#f87171';
    }
    document.querySelectorAll('.btn-submit-solution').forEach(btn => {
      btn.disabled = true;
      btn.textContent = 'Disqualified';
    });
  }

  // ================================================================
  // FULLSCREEN MANAGEMENT
  // Fullscreen API requires a direct user gesture — we show an overlay.
  // ================================================================
  const fsOverlay   = document.getElementById('fullscreen-overlay');
  const btnEnterFS  = document.getElementById('btn-enter-fullscreen');
  const btnSkipFS   = document.getElementById('btn-skip-fullscreen');
  const fsErrorDiv  = document.getElementById('fullscreen-error');
  let   fsActive    = false;

  // If already in fullscreen on load, dismiss overlay immediately
  if (document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement) {
    if (fsOverlay) fsOverlay.style.display = 'none';
    fsActive = true;
  }

  function requestFS() {
    console.log('[CRYTEX] Fullscreen requested');
    const el  = document.documentElement;
    const req = el.requestFullscreen || el.webkitRequestFullscreen || el.mozRequestFullScreen || el.msRequestFullscreen;
    if (!req) {
      console.warn('[CRYTEX] Fullscreen not supported by this browser. Continuing anyway.');
      if (fsOverlay) fsOverlay.style.display = 'none';
      fsActive = true;
      return;
    }
    req.call(el)
      .then(() => {
        console.log('[CRYTEX] Fullscreen entered');
        fsActive = true;
        if (fsOverlay) fsOverlay.style.display = 'none';
        if (fsErrorDiv) fsErrorDiv.style.display = 'none';
      })
      .catch(err => {
        console.error('[CRYTEX] Fullscreen error:', err);
        if (fsErrorDiv) {
          fsErrorDiv.innerHTML = 'Browser blocked fullscreen (' + (err.message || 'Permissions') + '). ' +
            '<div style="margin-top:0.6rem;"><button type="button" id="btn-force-continue" class="btn btn-primary" style="padding:0.4rem 0.9rem; font-size:0.85rem;">Continue to Dashboard</button></div>';
          fsErrorDiv.style.display = 'block';
          const forceBtn = document.getElementById('btn-force-continue');
          if (forceBtn) {
            forceBtn.onclick = () => {
              if (fsOverlay) fsOverlay.style.display = 'none';
              fsActive = true;
            };
          }
        }
      });
  }

  if (btnEnterFS) {
    btnEnterFS.addEventListener('click', requestFS);
  }

  if (btnSkipFS) {
    btnSkipFS.addEventListener('click', () => {
      console.log('[CRYTEX] Participant bypassed fullscreen requirement');
      if (fsOverlay) fsOverlay.style.display = 'none';
      fsActive = true;
    });
  }

  document.addEventListener('fullscreenchange', () => {
    if (document.fullscreenElement) {
      console.log('[CRYTEX] Fullscreen entered');
      fsActive = true;
      if (fsOverlay) fsOverlay.style.display = 'none';

      const acModal = document.getElementById('anticheat-modal');
      if (acModal) acModal.classList.remove('active');
    } else {
      console.log('[CRYTEX] Fullscreen exited');

      if (fsActive) {
        const now = Date.now();
        if (now - lastViolationTs < 3000) {
          console.log('[CRYTEX] Violation cooldown active — skipping duplicate report.');
          if (fsOverlay) fsOverlay.style.display = 'flex';
          fsActive = false;
          return;
        }
        lastViolationTs = now;

        fetch('/api/team/violation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            violation_type: 'FULLSCREEN_EXIT',
            details: 'Participant exited fullscreen mode'
          })
        })
          .then(r => r.json())
          .then(res => {
            const acModal  = document.getElementById('anticheat-modal');
            const acBadge  = document.getElementById('anticheat-strike-badge');
            const acTitle  = document.getElementById('anticheat-title');
            const acDesc   = document.getElementById('anticheat-desc');

            if (res.violation) {
              if (res.violation.is_disqualified) {
                isDisqualified = true;
                showDisqualifiedBanner();
                if (btnPlaceBid) btnPlaceBid.disabled = true;
                document.querySelectorAll('.btn-submit-solution').forEach(btn => {
                  btn.disabled = true;
                  btn.textContent = 'Disqualified';
                });
              } else {
                if (acBadge) acBadge.textContent = `Strike ${res.violation.strike_count} of 3`;
                if (acTitle) acTitle.textContent = res.violation.strike_count === 2
                  ? 'FINAL WARNING — STRIKE 2 OF 3'
                  : 'INTEGRITY WARNING';
                if (acDesc) acDesc.textContent =
                  `You exited fullscreen — Strike ${res.violation.strike_count} of 3 recorded. ` +
                  (res.violation.strike_count === 2
                    ? 'ONE MORE VIOLATION WILL DISQUALIFY YOUR TEAM.'
                    : 'Return to fullscreen to continue.');
                if (acModal) acModal.classList.add('active');
              }
            }
          })
          .catch(err => console.error('[CRYTEX] Could not record violation:', err));

        if (fsOverlay) fsOverlay.style.display = 'flex';
        fsActive = false;
      }
    }
  });

  const btnDismissWarning = document.getElementById('btn-dismiss-warning');
  if (btnDismissWarning) {
    btnDismissWarning.addEventListener('click', () => {
      const acModal = document.getElementById('anticheat-modal');
      if (acModal) acModal.classList.remove('active');
      requestFS();
    });
  }

  // ================================================================
  // BALANCE DISPLAY HELPER (Instant UI Refresh)
  // ================================================================
  function updateBalanceDisplay(newBalance) {
    if (typeof newBalance !== 'number') {
      newBalance = parseFloat(newBalance) || 0.0;
    }
    clientBalance = newBalance;
    const formattedNum = clientBalance.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (statBalance) {
      statBalance.textContent = `₹${formattedNum}`;
    }
    if (navTeamBalance) {
      navTeamBalance.textContent = formattedNum;
    }
  }

  // ================================================================
  // 1. Initialize Socket.IO with automatic reconnection
  // ================================================================
  const socket = io({
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    timeout: 20000
  });

  socket.on('connect', () => {
    console.log('[Socket] Connected to server.');
    socket.emit('request_sync');
  });

  socket.on('disconnect', () => {
    console.warn('[Socket] Disconnected from server. Waiting for auto-reconnect...');
  });

  // Authoritative State Synchronization
  socket.on('sync_state', (data) => {
    console.log('[Sync] Received authoritative sync:', data);
    if (data.team) {
      updateTeamState(data.team);
    }
    if (data.active_auction) {
      setLiveAuction(data.active_auction);
    } else {
      setNoAuction();
    }
    if (data.won_questions) {
      renderWonQuestions(data.won_questions);
    }
    if (data.leaderboard) {
      renderLeaderboard(data.leaderboard);
    }
  });

  socket.on('won_questions_update', (data) => {
    if (data && data.won_questions) {
      renderWonQuestions(data.won_questions);
    }
  });

  // Real-time Auction Events
  socket.on('auction_started', (data) => {
    console.log('[Auction] Started:', data);
    setLiveAuction(data);
    showToast(`📢 New Question: ${data.category}! 10s Reading Time started.`, 'info');
    try {
      if (window.soundFX) window.soundFX.playBidSound();
    } catch (e) {}
  });

  socket.on('bid_update', (data) => {
    console.log('[Auction] Bid Update:', data);
    handleBidUpdate(data);
  });

  socket.on('auction_ended', (data) => {
    console.log('[Auction] Ended:', data);
    handleAuctionEnded(data);
  });

  // Real-time Answer Evaluation Event: Instantly update balance and UI!
  socket.on('answer_result', (data) => {
    console.log('[Answer] Result broadcast:', data);
    if (data.team_id === window.TEAM_ID) {
      if (typeof data.new_balance === 'number') {
        updateBalanceDisplay(data.new_balance);
      }
      if (typeof data.questions_completed === 'number' && displaySolvedCount) {
        displaySolvedCount.textContent = data.questions_completed;
        questionsCompleted = data.questions_completed;
      }

      if (data.is_correct) {
        showToast(`🎉 Correct Solution! +₹${parseFloat(data.reward_credited).toFixed(2)} credited!`, 'success', 6000);
        try {
          if (window.soundFX) window.soundFX.playRewardSound();
        } catch (e) {
          console.warn('Sound error:', e);
        }
      } else {
        showToast('❌ Incorrect answer. Better luck on the next question!', 'warning', 5000);
      }
      refreshState();
    }
  });

  socket.on('leaderboard_update', (data) => {
    if (data.leaderboard) {
      renderLeaderboard(data.leaderboard);
    }
  });

  socket.on('team_violation', (data) => {
    if (data.team_id !== window.TEAM_ID) return;

    const acModal = document.getElementById('anticheat-modal');
    const acBadge = document.getElementById('anticheat-strike-badge');
    const acTitle = document.getElementById('anticheat-title');
    const acDesc  = document.getElementById('anticheat-desc');

    if (data.is_disqualified) {
      isDisqualified = true;
      if (acModal) acModal.classList.remove('active');
      showDisqualifiedBanner();

      if (btnPlaceBid) btnPlaceBid.disabled = true;
      if (bidWarningMsg) {
        bidWarningMsg.textContent = 'DISQUALIFIED — You may not participate further.';
        bidWarningMsg.style.color = '#f87171';
      }
      document.querySelectorAll('.btn-submit-solution').forEach(btn => {
        btn.disabled = true;
        btn.textContent = 'Disqualified';
      });
    } else {
      if (acBadge) acBadge.textContent = `Strike ${data.strike_count} of 3`;
      if (acTitle) acTitle.textContent = data.strike_count === 2
        ? 'FINAL WARNING — STRIKE 2 OF 3'
        : 'INTEGRITY WARNING';
      if (acDesc) acDesc.textContent =
        `You exited fullscreen — Strike ${data.strike_count} of 3 recorded. ` +
        (data.strike_count === 2
          ? 'ONE MORE VIOLATION WILL DISQUALIFY YOUR TEAM.'
          : 'Return to fullscreen to continue.');
      if (acModal) acModal.classList.add('active');
    }
  });

  // ================================================================
  // 2. Authoritative Timer Engine: Single 40s Countdown (Bid button visible after 10s)
  // ================================================================
  function startAuthoritativeTimer(biddingStartsAtIso, endsAtIso, initialSeconds) {
    if (timerInterval) clearInterval(timerInterval);

    const biddingStartsAtMs = biddingStartsAtIso ? new Date(biddingStartsAtIso).getTime() : 0;
    const endsAtMs = endsAtIso ? new Date(endsAtIso).getTime() : Date.now() + ((initialSeconds || 40) * 1000);

    const bidReadingNotice = document.getElementById('bid-reading-notice');
    const bidUnlockCountdown = document.getElementById('bid-unlock-countdown');

    function tick() {
      const now = Date.now();
      const totalMsLeft = endsAtMs - now;
      const totalSecLeft = Math.max(0, Math.ceil(totalMsLeft / 1000));

      // ALWAYS display the total remaining seconds (starts at 40s)
      if (auctionTimerDigits) auctionTimerDigits.textContent = totalSecLeft;
      if (auctionTimerLabel) auctionTimerLabel.textContent = 'Seconds';

      // 1. Initial 10 Seconds Question Reading Period (Timer: 40s down to 30s)
      if (biddingStartsAtMs && now < biddingStartsAtMs) {
        currentAuctionPhase = 'READING';
        const readingMsLeft = biddingStartsAtMs - now;
        const readingSecLeft = Math.max(0, Math.ceil(readingMsLeft / 1000));

        // Reading phase banner & styling
        if (auctionPhaseBanner) {
          auctionPhaseBanner.style.display = 'block';
          auctionPhaseBanner.className = 'phase-banner-reading';
          if (auctionPhaseIcon) auctionPhaseIcon.textContent = '📖';
          if (auctionPhaseText) auctionPhaseText.textContent = 'QUESTION READING TIME (Bidding opens at 30s)';
        }
        if (auctionTimerBox) {
          auctionTimerBox.classList.add('reading-phase');
          auctionTimerBox.classList.remove('warning');
        }
        if (auctionHero()) auctionHero().classList.remove('ending-soon');

        // HIDE THE BID BUTTON during the first 10 seconds!
        if (btnPlaceBid) {
          btnPlaceBid.style.display = 'none';
        }
        // Show reading notice placeholder with unlock countdown
        if (bidReadingNotice) {
          bidReadingNotice.style.display = 'block';
          if (bidUnlockCountdown) bidUnlockCountdown.textContent = readingSecLeft;
        }
        if (bidWarningMsg) {
          bidWarningMsg.textContent = 'Question reading time in progress (10s). Review the problem carefully!';
          bidWarningMsg.style.color = 'var(--accent-cyan)';
        }
        return;
      }

      // Transition from Reading Phase to Bidding Phase (at 10s elapsed / 30s mark)!
      if (currentAuctionPhase === 'READING') {
        currentAuctionPhase = 'BIDDING';
        showToast('⚡ 10s Reading time ended. Bidding is now OPEN!', 'info', 4000);
        try {
          if (window.soundFX) window.soundFX.playBiddingOpenSound();
        } catch (e) {}
      }

      // 2. Bidding Phase (30 seconds remaining down to 0)
      if (auctionPhaseBanner) {
        auctionPhaseBanner.style.display = 'block';
        auctionPhaseBanner.className = 'phase-banner-bidding';
        if (auctionPhaseIcon) auctionPhaseIcon.textContent = '🔥';
        if (auctionPhaseText) auctionPhaseText.textContent = 'BID TIME (30s) — PLACE BIDS NOW';
      }

      if (auctionTimerBox) {
        auctionTimerBox.classList.remove('reading-phase');
      }

      // HIDE reading notice & SHOW BID BUTTON!
      if (bidReadingNotice) {
        bidReadingNotice.style.display = 'none';
      }
      if (btnPlaceBid) {
        btnPlaceBid.style.display = 'inline-block';
      }

      // Warning pulse when <= 3 seconds left
      if (totalSecLeft <= 3 && totalSecLeft > 0) {
        if (auctionTimerBox) auctionTimerBox.classList.add('warning');
        if (auctionHero()) auctionHero().classList.add('ending-soon');
        if (window.soundFX && totalSecLeft !== lastWarningTick) {
          lastWarningTick = totalSecLeft;
          try { window.soundFX.playWarningTick(); } catch (e) {}
        }
      } else {
        if (auctionTimerBox) auctionTimerBox.classList.remove('warning');
        if (auctionHero()) auctionHero().classList.remove('ending-soon');
      }

      // Update bid button amount and eligibility
      if (activeAuction) {
        const nextBidAmount = activeAuction.current_bidder_id
          ? (parseFloat(activeAuction.current_bid) + 10.0)
          : parseFloat(activeAuction.starting_bid);
        if (btnBidAmount) btnBidAmount.textContent = nextBidAmount.toFixed(2);
        btnPlaceBid.innerHTML = `BID ₹<span id="btn-bid-amount">${nextBidAmount.toFixed(2)}</span>`;
        updateBidButtonState(nextBidAmount, activeAuction.current_bidder_id);
      }

      if (totalSecLeft <= 0) {
        clearInterval(timerInterval);
        if (auctionTimerDigits) auctionTimerDigits.textContent = '0';
        if (auctionTimerBox) auctionTimerBox.classList.remove('warning');
        if (btnPlaceBid) btnPlaceBid.disabled = true;
        if (bidWarningMsg) {
          bidWarningMsg.textContent = 'Auction closing...';
          bidWarningMsg.style.color = 'var(--text-muted)';
        }
      }
    }

    tick();
    timerInterval = setInterval(tick, 200);
  }

  function auctionHero() {
    return document.getElementById('auction-container');
  }

  // ================================================================
  // 3. UI State Handlers
  // ================================================================
  function setNoAuction() {
    activeAuction = null;
    currentAuctionPhase = 'BIDDING';
    if (timerInterval) clearInterval(timerInterval);
    if (auctionEmptyState) auctionEmptyState.style.display = 'block';
    if (auctionActiveState) auctionActiveState.style.display = 'none';
    if (auctionPhaseBanner) auctionPhaseBanner.style.display = 'none';
    if (auctionHero()) {
      auctionHero().classList.remove('active', 'ending-soon');
    }
  }

  function setLiveAuction(data) {
    activeAuction = {
      ...data,
      id: data.id ?? data.auction_id
    };

    if (auctionEmptyState) auctionEmptyState.style.display = 'none';
    if (auctionActiveState) auctionActiveState.style.display = 'block';
    if (auctionHero()) auctionHero().classList.add('active');

    if (auctionCategory) auctionCategory.textContent = data.category || 'General Math';
    if (auctionTypeBadge) auctionTypeBadge.textContent = data.question_type || 'Standard';
    if (auctionReward) auctionReward.textContent = `₹${parseFloat(data.reward).toFixed(2)}`;
    if (auctionSummaryText) auctionSummaryText.textContent = data.question_text || '';

    if (data.question_image && auctionImageContainer && auctionQuestionImage) {
      auctionQuestionImage.src = data.question_image;
      auctionImageContainer.style.display = 'block';
    } else if (auctionImageContainer) {
      auctionImageContainer.style.display = 'none';
    }

    if (auctionStartingBid) auctionStartingBid.textContent = `₹${parseFloat(data.starting_bid).toFixed(2)}`;
    if (auctionCurrentBid) auctionCurrentBid.textContent = `₹${parseFloat(data.current_bid).toFixed(2)}`;

    const nextBid = data.current_bidder_id ? (parseFloat(data.current_bid) + 10.0) : parseFloat(data.starting_bid);
    if (btnBidAmount) btnBidAmount.textContent = nextBid.toFixed(2);

    updateHighestBidderDisplay(data.current_bidder_id, data.current_bidder_code, data.current_bidder_name);
    updateBidButtonState(nextBid, data.current_bidder_id);

    startAuthoritativeTimer(data.bidding_starts_at_iso, data.ends_at_iso, data.time_remaining || 40);
  }

  function handleBidUpdate(data) {
    if (!activeAuction || activeAuction.id !== data.auction_id) {
      activeAuction = { id: data.auction_id };
    }
    activeAuction.current_bid = data.current_bid;
    activeAuction.current_bidder_id = data.current_bidder_id;
    activeAuction.starting_bid = activeAuction.starting_bid || data.current_bid;

    if (auctionCurrentBid) auctionCurrentBid.textContent = `₹${parseFloat(data.current_bid).toFixed(2)}`;
    if (btnBidAmount) btnBidAmount.textContent = parseFloat(data.next_bid).toFixed(2);

    // Bump animation on bid update
    if (auctionCurrentBid) {
      auctionCurrentBid.style.transform = 'scale(1.2)';
      auctionCurrentBid.style.transition = 'transform 0.15s ease';
      setTimeout(() => {
        auctionCurrentBid.style.transform = 'scale(1)';
      }, 150);
    }

    updateHighestBidderDisplay(data.current_bidder_id, data.current_bidder_code, data.current_bidder_name);
    updateBidButtonState(data.next_bid, data.current_bidder_id);

    try {
      if (window.soundFX) window.soundFX.playBidSound();
    } catch (e) {}

    // Bidding phase reset to 30s
    startAuthoritativeTimer(null, data.ends_at_iso, data.time_remaining || 30);
  }

  function updateHighestBidderDisplay(bidderId, bidderCode, bidderName) {
    if (!auctionHighestBidder) return;

    if (!bidderCode) {
      auctionHighestBidder.textContent = 'No Bids Yet';
      auctionHighestBidder.style.color = 'var(--accent-cyan)';
      if (leaderNotice) leaderNotice.style.display = 'none';
      return;
    }

    if (bidderId === window.TEAM_ID) {
      auctionHighestBidder.textContent = `YOU (${window.TEAM_CODE})`;
      auctionHighestBidder.style.color = '#34d399';
      if (leaderNotice) leaderNotice.style.display = 'block';
    } else {
      auctionHighestBidder.textContent = `${bidderCode}`;
      auctionHighestBidder.style.color = '#fbbf24';
      if (leaderNotice) leaderNotice.style.display = 'none';
    }
  }

  function updateBidButtonState(nextBid, leaderId) {
    if (!btnPlaceBid) return;
    if (bidWarningMsg) bidWarningMsg.textContent = '';

    if (currentAuctionPhase === 'READING') {
      btnPlaceBid.disabled = true;
      return;
    }

    if (isDisqualified) {
      btnPlaceBid.disabled = true;
      if (bidWarningMsg) bidWarningMsg.textContent = 'Account disqualified from bidding due to violations.';
      return;
    }

    if (questionsWon >= 5 || questionsCompleted >= 5) {
      btnPlaceBid.disabled = true;
      if (bidWarningMsg) bidWarningMsg.textContent = 'Maximum question limit reached (5 questions). You have completed your auction phase!';
      return;
    }

    if (leaderId === window.TEAM_ID) {
      btnPlaceBid.disabled = true;
      if (bidWarningMsg) bidWarningMsg.textContent = 'Your team currently holds the highest bid!';
      return;
    }

    if (clientBalance < nextBid) {
      btnPlaceBid.disabled = true;
      if (bidWarningMsg) bidWarningMsg.textContent = `Insufficient purse (₹${clientBalance.toFixed(2)} available, ₹${nextBid.toFixed(2)} needed).`;
      return;
    }

    btnPlaceBid.disabled = false;
  }

  function handleAuctionEnded(data) {
    if (timerInterval) clearInterval(timerInterval);
    try {
      if (window.soundFX) window.soundFX.playGavel();
    } catch (e) {}

    if (data.cancelled) {
      showToast('⚠️ The host cancelled this auction.', 'warning');
      setNoAuction();
      return;
    }

    if (data.has_winner) {
      if (data.winner_team_id === window.TEAM_ID) {
        showToast(`🎉 YOUR TEAM WON THE AUCTION for ₹${parseFloat(data.winning_bid).toFixed(2)}! Question added to your repository.`, 'success', 8000);
        // Immediately deduct winning bid from clientBalance so UI updates in 0ms
        const deduction = parseFloat(data.winning_bid) || 0.0;
        updateBalanceDisplay(Math.max(0, clientBalance - deduction));
        refreshState();
      } else {
        showToast(`🔨 Auction ended. Won by Team ${data.winner_team_code} for ₹${parseFloat(data.winning_bid).toFixed(2)}.`, 'info');
      }
    } else {
      showToast('Auction expired with no bids placed.', 'info');
    }

    setTimeout(() => {
      setNoAuction();
    }, 2000);
  }

  // ================================================================
  // 4. Bidding Handler
  // ================================================================
  if (btnPlaceBid) {
    btnPlaceBid.addEventListener('click', async () => {
      if (!activeAuction || btnPlaceBid.disabled || isDisqualified || currentAuctionPhase === 'READING') return;

      btnPlaceBid.disabled = true;
      if (bidWarningMsg) bidWarningMsg.textContent = 'Placing bid...';

      // Primary: Socket.IO bid event
      socket.emit('place_bid', { auction_id: activeAuction.id });

      // Fallback: HTTP endpoint if no socket ack
      const fallbackTimer = setTimeout(async () => {
        try {
          const resp = await fetch('/api/team/bid', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ auction_id: activeAuction.id })
          });
          const result = await resp.json();
          if (!result.success) {
            if (bidWarningMsg) bidWarningMsg.textContent = result.error;
            showToast(`Bid rejected: ${result.error}`, 'danger');
          }
        } catch (err) {
          console.error('Bid error:', err);
        }
      }, 800);

      socket.once('bid_success', () => clearTimeout(fallbackTimer));
      socket.once('bid_error', (data) => {
        clearTimeout(fallbackTimer);
        if (bidWarningMsg) bidWarningMsg.textContent = data.error;
        showToast(`Bid rejected: ${data.error}`, 'danger');
      });
    });
  }

  // ================================================================
  // 5. 5-Question Repository Rendering & Solving Flow
  // ================================================================
  function renderWonQuestions(wonQuestions) {
    if (!wonQuestionsContainer) return;

    const count = wonQuestions.length;
    if (repoCount) repoCount.textContent = count;
    if (displayWonCount) displayWonCount.textContent = count;
    questionsWon = count;

    if (count === 0) {
      if (wonEmptyMsg) wonEmptyMsg.style.display = 'block';
      wonQuestionsContainer.innerHTML = '';
      return;
    }

    if (wonEmptyMsg) wonEmptyMsg.style.display = 'none';

    let html = '';
    wonQuestions.forEach(q => {
      const isSolved = q.is_solved;
      html += `
        <div class="card won-question-item" data-auction-id="${q.auction_id}" style="background: rgba(14, 21, 38, 0.7); border: 1px solid var(--border-color); padding: 1.25rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; flex-wrap: wrap; gap: 0.5rem;">
            <div>
              <span class="category-tag" style="font-size: 0.8rem;">${q.category}</span>
              <span style="font-size: 0.8rem; color: var(--text-muted); margin-left: 0.5rem;">Auction #${q.auction_id}</span>
            </div>
            <div>
              <span class="reward-tag" style="font-size: 0.85rem;">Reward: ₹${parseFloat(q.reward).toFixed(2)}</span>
              <span style="font-size: 0.8rem; color: #fbbf24; margin-left: 0.5rem;">(Paid: ₹${parseFloat(q.winning_bid).toFixed(2)})</span>
            </div>
          </div>

          <div style="font-size: 1.05rem; font-weight: 600; color: #fff; margin-bottom: 0.75rem;">
            ${q.question_text}
          </div>

          ${q.question_image ? `
            <div style="text-align: center; margin: 0.75rem 0;">
              <img src="${q.question_image}" alt="Question Image" style="max-height: 220px; max-width: 100%; border-radius: 6px; border: 1px solid var(--border-color); object-fit: contain;">
            </div>
          ` : ''}

          <div style="margin-top: 1rem; padding-top: 0.75rem; border-top: 1px solid rgba(255,255,255,0.06);">
            ${isSolved ? `
              <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
                <div>
                  ${q.is_correct ? `
                    <span style="background: rgba(16,185,129,0.2); color: #34d399; font-weight: 700; padding: 0.35rem 0.8rem; border-radius: 6px; font-size: 0.9rem;">
                      ✅ CORRECT SOLUTION (+₹${parseFloat(q.reward_credited).toFixed(2)})
                    </span>
                  ` : `
                    <span style="background: rgba(239,68,68,0.2); color: #f87171; font-weight: 700; padding: 0.35rem 0.8rem; border-radius: 6px; font-size: 0.9rem;">
                      ❌ INCORRECT ATTEMPT (₹0.00)
                    </span>
                  `}
                </div>
                <div style="font-size: 0.85rem; color: var(--text-muted);">
                  Submitted Answer: <strong style="color: #fff;">${q.submitted_answer || ''}</strong>
                </div>
              </div>
            ` : `
              <div id="solve-form-${q.auction_id}" style="display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap;">
                <input type="text" id="solve-input-${q.auction_id}" class="form-control" placeholder="Enter integer answer..." style="max-width: 250px; font-weight: 700; font-size: 1.05rem;">
                <button class="btn btn-primary btn-submit-solution" data-auction-id="${q.auction_id}" style="font-weight: 700; padding: 0.5rem 1.25rem;">
                  Submit Solution
                </button>
                <div id="solve-feedback-${q.auction_id}" style="font-size: 0.9rem; font-weight: 600;"></div>
              </div>
            `}
          </div>
        </div>
      `;
    });

    wonQuestionsContainer.innerHTML = html;
    bindSolveButtons();
  }

  function bindSolveButtons() {
    document.querySelectorAll('.btn-submit-solution').forEach(btn => {
      if (isDisqualified) {
        btn.disabled = true;
        btn.textContent = 'Disqualified';
        return;
      }
      btn.onclick = async () => {
        const auctionId = btn.getAttribute('data-auction-id');
        const input = document.getElementById(`solve-input-${auctionId}`);
        const feedback = document.getElementById(`solve-feedback-${auctionId}`);

        if (!input || !input.value.trim()) {
          if (feedback) {
            feedback.textContent = 'Please enter an answer.';
            feedback.style.color = 'var(--accent-red)';
          }
          return;
        }

        const answerText = input.value.trim();

        // Lock button immediately to prevent double submissions
        btn.disabled = true;
        btn.textContent = 'Submitting...';
        if (feedback) {
          feedback.textContent = 'Evaluating answer...';
          feedback.style.color = 'var(--accent-cyan)';
        }

        try {
          const resp = await fetch('/api/team/submit-answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              auction_id: auctionId,
              answer: answerText
            })
          });

          const res = await resp.json();
          if (res.success) {
            const isCorrect = res.result.is_correct;

            // 1. Immediately update client balance and UI without requiring login!
            if (res.result && typeof res.result.new_balance === 'number') {
              updateBalanceDisplay(res.result.new_balance);
            }
            if (res.result && typeof res.result.questions_completed === 'number' && displaySolvedCount) {
              displaySolvedCount.textContent = res.result.questions_completed;
              questionsCompleted = res.result.questions_completed;
            }

            if (isCorrect) {
              if (feedback) {
                feedback.textContent = `Correct! +₹${parseFloat(res.result.reward_credited).toFixed(2)}`;
                feedback.style.color = '#34d399';
              }
              try {
                if (window.soundFX) window.soundFX.playRewardSound();
              } catch (e) {
                console.warn('Sound error:', e);
              }
              showToast(`🎉 Correct answer! +₹${parseFloat(res.result.reward_credited).toFixed(2)} credited!`, 'success');
            } else {
              if (feedback) {
                feedback.textContent = 'Incorrect answer (₹0.00).';
                feedback.style.color = '#f87171';
              }
              showToast('Incorrect answer. Zero reward credited.', 'warning');
            }

            // Re-render won questions list from authoritative server response
            if (res.won_questions) {
              renderWonQuestions(res.won_questions);
            }
            refreshState();
          } else {
            btn.disabled = false;
            btn.textContent = 'Submit Solution';
            if (feedback) {
              feedback.textContent = res.error || 'Submission rejected.';
              feedback.style.color = 'var(--accent-red)';
            }
            showToast(`Submission rejected: ${res.error}`, 'danger');
          }
        } catch (err) {
          btn.disabled = false;
          btn.textContent = 'Submit Solution';
          if (feedback) {
            feedback.textContent = 'Network or server error during submission.';
            feedback.style.color = 'var(--accent-red)';
          }
          console.error('Submit error:', err);
        }
      };
    });
  }

  // ================================================================
  // 6. Refresh Team State & Ledger
  // ================================================================
  async function refreshState() {
    try {
      const resp = await fetch('/api/team/state');
      const data = await resp.json();
      if (data.team) updateTeamState(data.team);
      if (data.won_questions) renderWonQuestions(data.won_questions);
      refreshLedger();
    } catch (e) {
      console.error('Error refreshing state:', e);
    }
  }

  function updateTeamState(team) {
    updateBalanceDisplay(team.current_balance);
    questionsWon = team.questions_won;
    questionsCompleted = team.questions_completed;
    isDisqualified = team.is_disqualified;

    if (statRank && team.rank) statRank.textContent = `#${team.rank}`;
    if (displayWonCount) displayWonCount.textContent = team.questions_won;
    if (displaySolvedCount) displaySolvedCount.textContent = team.questions_completed;

    if (isDisqualified) {
      showDisqualifiedBanner();
      if (btnPlaceBid) btnPlaceBid.disabled = true;
      if (bidWarningMsg) {
        bidWarningMsg.textContent = 'DISQUALIFIED — You may not participate further.';
        bidWarningMsg.style.color = '#f87171';
      }
      document.querySelectorAll('.btn-submit-solution').forEach(btn => {
        btn.disabled = true;
        btn.textContent = 'Disqualified';
      });
    }
  }

  function showDisqualifiedBanner() {
    if (document.getElementById('disqualified-banner')) return;

    const banner = document.createElement('div');
    banner.id = 'disqualified-banner';
    banner.style.cssText = `
      position: fixed; top: 0; left: 0; right: 0; z-index: 99998;
      background: linear-gradient(135deg, rgba(185,28,28,0.97), rgba(127,29,29,0.97));
      border-bottom: 3px solid #f87171;
      color: #fff; text-align: center;
      padding: 1.2rem 1.5rem;
      font-size: 1.1rem; font-weight: 800;
      letter-spacing: 0.04em;
      backdrop-filter: blur(6px);
    `;
    banner.innerHTML = `
      🚫 TEAM DISQUALIFIED — 3 STRIKES REACHED
      <div style="font-size: 0.85rem; font-weight: 400; margin-top: 0.25rem; color: #fca5a5;">
        Your team has been removed from the competition due to 3 integrity violations.
        All records and balances are preserved.
      </div>
    `;
    document.body.prepend(banner);
  }

  async function refreshLedger() {
    try {
      const resp = await fetch('/api/team/transactions');
      const data = await resp.json();
      if (!transactionsBody || !data.transactions) return;

      let html = '';
      data.transactions.slice(0, 15).forEach(tx => {
        const isPos = parseFloat(tx.amount) > 0;
        let badgeBg = 'rgba(59,130,246,0.2)';
        let badgeColor = '#60a5fa';
        if (tx.transaction_type === 'REWARD') {
          badgeBg = 'rgba(16,185,129,0.2)';
          badgeColor = '#34d399';
        } else if (tx.transaction_type === 'BID_PAYMENT') {
          badgeBg = 'rgba(239,68,68,0.2)';
          badgeColor = '#f87171';
        }

        html += `
          <tr>
            <td style="font-size: 0.8rem; color: var(--text-muted);">${tx.created_at_formatted || ''}</td>
            <td><span style="font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.4rem; border-radius: 4px; background: ${badgeBg}; color: ${badgeColor};">${tx.transaction_type}</span></td>
            <td style="font-weight: 700; color: ${isPos ? '#34d399' : '#f87171'};">${isPos ? '+' : ''}₹${parseFloat(tx.amount).toFixed(2)}</td>
            <td style="font-weight: 600;">₹${parseFloat(tx.balance_after).toFixed(2)}</td>
          </tr>
        `;
      });
      transactionsBody.innerHTML = html;
    } catch (e) {
      console.error('Error refreshing ledger:', e);
    }
  }

  if (btnRefreshLedger) {
    btnRefreshLedger.addEventListener('click', refreshLedger);
  }

  // ================================================================
  // 7. Render Leaderboard
  // ================================================================
  function renderLeaderboard(leaderboard) {
    if (!leaderboardBody) return;

    let html = '';
    leaderboard.forEach(entry => {
      const isMe = entry.team_id === window.TEAM_ID;
      const rowStyle = isMe ? 'background: rgba(59, 130, 246, 0.15); font-weight: 700;' : '';

      html += `
        <tr style="${rowStyle}">
          <td>
            <span class="badge" style="${entry.rank <= 3 ? 'background: var(--accent-gold); color: #000;' : 'background: rgba(255,255,255,0.08);'}">
              #${entry.rank}
            </span>
          </td>
          <td>
            <div style="font-weight: 700; color: ${isMe ? '#60a5fa' : '#fff'};">
              ${entry.team_code} ${isMe ? '(YOU)' : ''}
            </div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">${entry.team_name}</div>
          </td>
          <td style="color: #34d399; font-weight: 700;">
            ₹${parseFloat(entry.current_balance).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </td>
          <td>${entry.correct_answers}</td>
          <td>${entry.questions_won}</td>
        </tr>
      `;
    });
    leaderboardBody.innerHTML = html;
  }
});
