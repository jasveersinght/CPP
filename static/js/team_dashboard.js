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
  const auctionTimerBox = document.getElementById('auction-timer-box');
  const auctionTimerDigits = document.getElementById('auction-timer-digits');
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
  let lastViolationTs = 0;  // timestamp of last recorded violation (for cooldown guard)

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
  // FULLSCREEN MANAGEMENT (Bug 1 Fix)
  // Fullscreen API requires a direct user gesture — we show an overlay.
  // ================================================================
  const fsOverlay   = document.getElementById('fullscreen-overlay');
  const btnEnterFS  = document.getElementById('btn-enter-fullscreen');
  const fsErrorDiv  = document.getElementById('fullscreen-error');
  let   fsActive    = false;  // true once participant has entered fullscreen

  function requestFS() {
    console.log('[CRYTEX] Fullscreen requested');
    const el  = document.documentElement;
    const req = el.requestFullscreen || el.webkitRequestFullscreen || el.mozRequestFullScreen || el.msRequestFullscreen;
    if (!req) {
      // Browser doesn't support fullscreen — just dismiss overlay and continue
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
          fsErrorDiv.textContent = 'Could not enter fullscreen: ' + err.message + '. Please try again or use F11.';
          fsErrorDiv.style.display = 'block';
        }
      });
  }

  if (btnEnterFS) {
    btnEnterFS.addEventListener('click', requestFS);
  }

  document.addEventListener('fullscreenchange', () => {
    if (document.fullscreenElement) {
      // Entered fullscreen
      console.log('[CRYTEX] Fullscreen entered');
      fsActive = true;
      if (fsOverlay) fsOverlay.style.display = 'none';

      // Dismiss anticheat modal if open (team returned to fullscreen)
      const acModal = document.getElementById('anticheat-modal');
      if (acModal) acModal.classList.remove('active');
    } else {
      // Exited fullscreen
      console.log('[CRYTEX] Fullscreen exited');

      if (fsActive) {
        // Cooldown guard: prevent duplicate strikes from rapid overlapping browser events.
        // (Some browsers fire fullscreenchange twice in quick succession.)
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
                // Strike 3 — permanent ban
                isDisqualified = true;
                showDisqualifiedBanner();
                if (btnPlaceBid) btnPlaceBid.disabled = true;
                document.querySelectorAll('.btn-submit-solution').forEach(btn => {
                  btn.disabled = true;
                  btn.textContent = 'Disqualified';
                });
              } else {
                // Strike 1 or 2 — show warning modal
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

        // Show re-enter fullscreen overlay so they can get back in
        if (fsOverlay) fsOverlay.style.display = 'flex';
        fsActive = false;
      }
    }
  });

  // "I Understand & Return to Fullscreen" button in anticheat modal → re-enter
  const btnDismissWarning = document.getElementById('btn-dismiss-warning');
  if (btnDismissWarning) {
    btnDismissWarning.addEventListener('click', () => {
      const acModal = document.getElementById('anticheat-modal');
      if (acModal) acModal.classList.remove('active');
      requestFS();
    });
  }

  // 1. Initialize Socket.IO with automatic reconnection
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
    showToast(`📢 New Auction Live: ${data.category}! Starting at ₹${data.starting_bid}`, 'info');
    if (window.soundFX) window.soundFX.playBidSound();
  });

  socket.on('bid_update', (data) => {
    console.log('[Auction] Bid Update:', data);
    handleBidUpdate(data);
  });

  socket.on('auction_ended', (data) => {
    console.log('[Auction] Ended:', data);
    handleAuctionEnded(data);
  });

  socket.on('answer_result', (data) => {
    console.log('[Answer] Result broadcast:', data);
    if (data.team_id === window.TEAM_ID) {
      if (data.is_correct) {
        showToast(`🎉 Correct Solution! +₹${parseFloat(data.reward_credited).toFixed(2)} credited!`, 'success', 6000);
        if (window.soundFX) window.soundFX.playRewardSound();
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

  // Real-time: server confirms a violation was recorded for THIS team
  socket.on('team_violation', (data) => {
    if (data.team_id !== window.TEAM_ID) return; // not our team

    const acModal = document.getElementById('anticheat-modal');
    const acBadge = document.getElementById('anticheat-strike-badge');
    const acTitle = document.getElementById('anticheat-title');
    const acDesc  = document.getElementById('anticheat-desc');

    if (data.is_disqualified) {
      // Strike 3 — permanently lock the dashboard
      isDisqualified = true;

      // Hide the anticheat-modal and show a permanent disqualification banner instead
      if (acModal) acModal.classList.remove('active');
      showDisqualifiedBanner();

      // Disable bid button permanently
      if (btnPlaceBid) {
        btnPlaceBid.disabled = true;
      }
      if (bidWarningMsg) {
        bidWarningMsg.textContent = 'DISQUALIFIED — You may not participate further.';
        bidWarningMsg.style.color = '#f87171';
      }

      // Disable all unsolved answer submission buttons
      document.querySelectorAll('.btn-submit-solution').forEach(btn => {
        btn.disabled = true;
        btn.textContent = 'Disqualified';
      });
    } else {
      // Strike 1 or 2 — show warning, allow return to fullscreen
      if (acBadge) acBadge.textContent = `Strike ${data.strike_count} of 3`;
      if (acTitle) acTitle.textContent  = data.strike_count === 2
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

  // 2. Authoritative Timer Engine
  function startAuthoritativeTimer(endsAtIso, initialSeconds) {
    if (timerInterval) clearInterval(timerInterval);

    const endsAtMs = endsAtIso ? new Date(endsAtIso).getTime() : Date.now() + (initialSeconds * 1000);

    function tick() {
      const now = Date.now();
      const diffMs = endsAtMs - now;
      const secondsLeft = Math.max(0, Math.ceil(diffMs / 1000));

      if (auctionTimerDigits) {
        auctionTimerDigits.textContent = secondsLeft;
      }

      if (secondsLeft <= 3 && secondsLeft > 0) {
        auctionTimerBox.classList.add('warning');
        if (auctionHero()) auctionHero().classList.add('ending-soon');
        if (window.soundFX && secondsLeft !== lastWarningTick) {
          lastWarningTick = secondsLeft;
          window.soundFX.playWarningTick();
        }
      } else {
        auctionTimerBox.classList.remove('warning');
        if (auctionHero()) auctionHero().classList.remove('ending-soon');
      }

      if (secondsLeft <= 0) {
        clearInterval(timerInterval);
        if (auctionTimerDigits) auctionTimerDigits.textContent = '0';
        auctionTimerBox.classList.remove('warning');
        btnPlaceBid.disabled = true;
        bidWarningMsg.textContent = 'Auction closing...';
      }
    }

    tick();
    timerInterval = setInterval(tick, 200);
  }

  function auctionHero() {
    return document.getElementById('auction-container');
  }

  // 3. UI State Handlers
  function setNoAuction() {
    activeAuction = null;
    if (timerInterval) clearInterval(timerInterval);
    auctionEmptyState.style.display = 'block';
    auctionActiveState.style.display = 'none';
    if (auctionHero()) {
      auctionHero().classList.remove('active', 'ending-soon');
    }
  }

  function setLiveAuction(data) {
    // Preserve auction ID normalization fix (Requirement 8)
    activeAuction = {
      ...data,
      id: data.id ?? data.auction_id
    };

    auctionEmptyState.style.display = 'none';
    auctionActiveState.style.display = 'block';
    if (auctionHero()) auctionHero().classList.add('active');

    auctionCategory.textContent = data.category || 'General Math';
    auctionTypeBadge.textContent = data.question_type || 'Standard';
    auctionReward.textContent = `₹${parseFloat(data.reward).toFixed(2)}`;
    auctionSummaryText.textContent = data.question_text || '';

    // Handle question image (JPG / JPEG / PNG)
    if (data.question_image && auctionImageContainer && auctionQuestionImage) {
      auctionQuestionImage.src = data.question_image;
      auctionImageContainer.style.display = 'block';
    } else if (auctionImageContainer) {
      auctionImageContainer.style.display = 'none';
    }

    auctionStartingBid.textContent = `₹${parseFloat(data.starting_bid).toFixed(2)}`;
    auctionCurrentBid.textContent = `₹${parseFloat(data.current_bid).toFixed(2)}`;

    // Calculate next bid
    const nextBid = data.current_bidder_id ? (parseFloat(data.current_bid) + 10.0) : parseFloat(data.starting_bid);
    btnBidAmount.textContent = nextBid.toFixed(2);

    updateHighestBidderDisplay(data.current_bidder_id, data.current_bidder_code, data.current_bidder_name);
    updateBidButtonState(nextBid, data.current_bidder_id);

    startAuthoritativeTimer(data.ends_at_iso, data.time_remaining || 10);
  }

  function handleBidUpdate(data) {
    if (!activeAuction || activeAuction.id !== data.auction_id) {
      activeAuction = { id: data.auction_id };
    }
    activeAuction.current_bid = data.current_bid;
    activeAuction.current_bidder_id = data.current_bidder_id;

    auctionCurrentBid.textContent = `₹${parseFloat(data.current_bid).toFixed(2)}`;
    btnBidAmount.textContent = parseFloat(data.next_bid).toFixed(2);

    // Bump animation
    auctionCurrentBid.style.transform = 'scale(1.2)';
    auctionCurrentBid.style.transition = 'transform 0.15s ease';
    setTimeout(() => {
      auctionCurrentBid.style.transform = 'scale(1)';
    }, 150);

    updateHighestBidderDisplay(data.current_bidder_id, data.current_bidder_code, data.current_bidder_name);
    updateBidButtonState(data.next_bid, data.current_bidder_id);

    if (window.soundFX) window.soundFX.playBidSound();
    startAuthoritativeTimer(data.ends_at_iso, data.time_remaining || 10);
  }

  function updateHighestBidderDisplay(bidderId, bidderCode, bidderName) {
    if (!bidderCode) {
      auctionHighestBidder.textContent = 'No Bids Yet';
      auctionHighestBidder.style.color = 'var(--accent-cyan)';
      leaderNotice.style.display = 'none';
      return;
    }

    if (bidderId === window.TEAM_ID) {
      auctionHighestBidder.textContent = `YOU (${window.TEAM_CODE})`;
      auctionHighestBidder.style.color = '#34d399';
      leaderNotice.style.display = 'block';
    } else {
      auctionHighestBidder.textContent = `${bidderCode}`;
      auctionHighestBidder.style.color = '#fbbf24';
      leaderNotice.style.display = 'none';
    }
  }

  function updateBidButtonState(nextBid, leaderId) {
    bidWarningMsg.textContent = '';

    if (isDisqualified) {
      btnPlaceBid.disabled = true;
      bidWarningMsg.textContent = 'Account disqualified from bidding due to violations.';
      return;
    }

    if (questionsWon >= 5 || questionsCompleted >= 5) {
      btnPlaceBid.disabled = true;
      bidWarningMsg.textContent = 'Maximum question limit reached (5 questions). You have completed your auction phase!';
      return;
    }

    if (leaderId === window.TEAM_ID) {
      btnPlaceBid.disabled = true;
      bidWarningMsg.textContent = 'Your team currently holds the highest bid!';
      return;
    }

    if (clientBalance < nextBid) {
      btnPlaceBid.disabled = true;
      bidWarningMsg.textContent = `Insufficient purse (₹${clientBalance.toFixed(2)} available, ₹${nextBid.toFixed(2)} needed).`;
      return;
    }

    btnPlaceBid.disabled = false;
  }

  function handleAuctionEnded(data) {
    if (timerInterval) clearInterval(timerInterval);
    if (window.soundFX) window.soundFX.playGavel();

    if (data.cancelled) {
      showToast('⚠️ The host cancelled this auction.', 'warning');
      setNoAuction();
      return;
    }

    if (data.has_winner) {
      if (data.winner_team_id === window.TEAM_ID) {
        showToast(`🎉 YOUR TEAM WON THE AUCTION for ₹${parseFloat(data.winning_bid).toFixed(2)}! Question added to your repository.`, 'success', 8000);
        // Refresh state to fetch updated won questions queue
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

  // 4. Bidding Handler
  btnPlaceBid.addEventListener('click', async () => {
    if (!activeAuction || btnPlaceBid.disabled || isDisqualified) return;

    btnPlaceBid.disabled = true;
    bidWarningMsg.textContent = 'Placing bid...';

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
          bidWarningMsg.textContent = result.error;
          showToast(`Bid rejected: ${result.error}`, 'danger');
        }
      } catch (err) {
        console.error('Bid error:', err);
      }
    }, 800);

    socket.once('bid_success', () => clearTimeout(fallbackTimer));
    socket.once('bid_error', (data) => {
      clearTimeout(fallbackTimer);
      bidWarningMsg.textContent = data.error;
      showToast(`Bid rejected: ${data.error}`, 'danger');
    });
  });

  // 5. 5-Question Repository Rendering & Solving Flow
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
            if (isCorrect) {
              if (feedback) {
                feedback.textContent = `Correct! +₹${parseFloat(res.result.reward_credited).toFixed(2)}`;
                feedback.style.color = '#34d399';
              }
              if (window.soundFX) window.soundFX.playRewardSound();
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
              setTimeout(() => renderWonQuestions(res.won_questions), 600);
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
            feedback.textContent = 'Network error submitting solution.';
            feedback.style.color = 'var(--accent-red)';
          }
          showToast('Network error submitting solution.', 'danger');
        }
      };
    });
  }

  // 6. Refresh Team State & Ledger
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
    clientBalance = parseFloat(team.current_balance);
    questionsWon = team.questions_won;
    questionsCompleted = team.questions_completed;
    isDisqualified = team.is_disqualified;

    const formatted = `₹${clientBalance.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    if (statBalance) statBalance.textContent = formatted;
    if (navTeamBalance) navTeamBalance.textContent = formatted;
    if (statRank && team.rank) statRank.textContent = `#${team.rank}`;
    if (displayWonCount) displayWonCount.textContent = team.questions_won;
    if (displaySolvedCount) displaySolvedCount.textContent = team.questions_completed;

    // If team is disqualified (including after page refresh), lock UI immediately
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

  /**
   * Renders (or ensures) the permanent disqualification banner on the page.
   * Safe to call multiple times — banner is only inserted once.
   */
  function showDisqualifiedBanner() {
    if (document.getElementById('disqualified-banner')) return; // already shown

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

    // Also hide the fullscreen overlay / anticheat modal — they're no longer relevant
    if (fsOverlay) fsOverlay.style.display = 'none';
    const acModal = document.getElementById('anticheat-modal');
    if (acModal) acModal.classList.remove('active');
  }

  async function refreshLedger() {
    try {
      const resp = await fetch('/api/team/transactions');
      const data = await resp.json();
      if (data.transactions && transactionsBody) {
        let html = '';
        data.transactions.slice(0, 15).forEach(tx => {
          const isPos = parseFloat(tx.amount) > 0;
          const bgBadge = tx.transaction_type === 'REWARD' ? 'rgba(16,185,129,0.2); color:#34d399;' :
            tx.transaction_type === 'BID_PAYMENT' ? 'rgba(239,68,68,0.2); color:#f87171;' : 'rgba(59,130,246,0.2); color:#60a5fa;';
          html += `
            <tr>
              <td style="font-size: 0.8rem; color: var(--text-muted);">${tx.created_at_formatted}</td>
              <td>
                <span style="font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.4rem; border-radius: 4px; background: ${bgBadge}">
                  ${tx.transaction_type}
                </span>
              </td>
              <td style="font-weight: 700; color: ${isPos ? '#34d399' : '#f87171'};">
                ${isPos ? '+' : ''}₹${parseFloat(tx.amount).toFixed(2)}
              </td>
              <td style="font-weight: 600;">₹${parseFloat(tx.balance_after).toFixed(2)}</td>
            </tr>
          `;
        });
        transactionsBody.innerHTML = html;
      }
    } catch (e) {
      console.error('Error refreshing transactions ledger:', e);
    }
  }

  if (btnRefreshLedger) {
    btnRefreshLedger.addEventListener('click', refreshLedger);
  }

  function renderLeaderboard(leaderboard) {
    if (!leaderboardBody) return;
    let html = '';
    leaderboard.forEach(entry => {
      const isCurrentTeam = entry.team_id === window.TEAM_ID;
      html += `
        <tr style="${isCurrentTeam ? 'background: rgba(59, 130, 246, 0.15); font-weight: 700;' : ''}">
          <td style="font-weight: 800; color: ${entry.rank === 1 ? '#fbbf24' : entry.rank === 2 ? '#94a3b8' : entry.rank === 3 ? '#b45309' : 'inherit'};">
            #${entry.rank}
          </td>
          <td>
            ${entry.team_code}
            ${isCurrentTeam ? '<span style="color: #34d399; font-size: 0.75rem; margin-left: 0.25rem;">(YOU)</span>' : ''}
            <div style="font-size: 0.75rem; color: var(--text-muted); font-weight: normal;">${entry.team_name}</div>
          </td>
          <td style="color: #34d399; font-weight: 700;">₹${parseFloat(entry.current_balance).toFixed(2)}</td>
          <td>${entry.correct_answers}</td>
          <td>${entry.questions_won}</td>
        </tr>
      `;
    });
    leaderboardBody.innerHTML = html;
  }
});
