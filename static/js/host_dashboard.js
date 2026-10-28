// MATH AUCTION - Host Dashboard Controller
// 80-Team Event Scale & System Surveillance Engine

document.addEventListener('DOMContentLoaded', () => {
  const hostAuctionCard = document.getElementById('host-auction-card');
  const hostNoAuction = document.getElementById('host-no-auction');
  const hostActiveAuction = document.getElementById('host-active-auction');
  const hostAuctionStatusBadge = document.getElementById('host-auction-status-badge');
  const hostCategory = document.getElementById('host-category');
  const hostType = document.getElementById('host-type');
  const hostReward = document.getElementById('host-reward');
  const hostQuestionText = document.getElementById('host-question-text');
  const hostImageContainer = document.getElementById('host-image-container');
  const hostQuestionImage = document.getElementById('host-question-image');
  const hostStartingBid = document.getElementById('host-starting-bid');
  const hostCurrentBid = document.getElementById('host-current-bid');
  const hostCurrentBidder = document.getElementById('host-current-bidder');
  const hostTimerBox = document.getElementById('host-timer-box');
  const hostTimerDigits = document.getElementById('host-timer-digits');
  const hostActiveAuctionId = document.getElementById('host-active-auction-id');
  const btnCancelAuction = document.getElementById('btn-cancel-auction');
  const btnEndAuction = document.getElementById('btn-end-auction');
  const hostBidsBody = document.getElementById('host-bids-body');
  const hostTeamsBody = document.getElementById('host-teams-body');
  const hostViolationsBody = document.getElementById('host-violations-body');

  // Telemetry DOM elements
  const statOnlineTeams = document.getElementById('stat-online-teams');
  const statCurrentAuctionId = document.getElementById('stat-current-auction-id');
  const statCurrentBid = document.getElementById('stat-current-bid');
  const statCurrentBidder = document.getElementById('stat-current-bidder');
  const statRegisteredTeams = document.getElementById('stat-registered-teams');
  const statAvailableQuestions = document.getElementById('stat-available-questions');

  // Add Team Modal DOM elements
  const modalAddTeam = document.getElementById('modal-add-team');
  const btnOpenAddTeamModal = document.getElementById('btn-open-add-team-modal');
  const btnCloseAddTeamModal = document.getElementById('btn-close-add-team-modal');
  const btnCancelAddTeam = document.getElementById('btn-cancel-add-team');
  const btnSubmitAddTeam = document.getElementById('btn-submit-add-team');
  const addTeamName = document.getElementById('add-team-name');
  const addTeamCode = document.getElementById('add-team-code');
  const addTeamPassword = document.getElementById('add-team-password');
  const addTeamBalance = document.getElementById('add-team-balance');
  const addTeamErrorMsg = document.getElementById('add-team-error-msg');
  const addTeamSuccessMsg = document.getElementById('add-team-success-msg');

  // Reset Test Data DOM element
  const btnResetTestData = document.getElementById('btn-reset-test-data');

  // Search input
  const inputSearchTeams = document.getElementById('input-search-teams');

  let activeAuction = null;
  let timerInterval = null;

  // Initialize Socket.IO
  const socket = io({
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 1000
  });

  socket.on('connect', () => {
    console.log('[Host Socket] Connected.');
    socket.emit('request_sync');
  });

  socket.on('sync_state', (data) => {
    console.log('[Host Sync]', data);
    if (data.online_teams !== undefined && statOnlineTeams) {
      statOnlineTeams.textContent = data.online_teams;
    }
    if (data.active_auction) {
      setLiveAuction(data.active_auction);
    } else {
      setNoAuction();
    }
  });

  socket.on('online_teams_update', (data) => {
    if (data && data.online_teams !== undefined && statOnlineTeams) {
      statOnlineTeams.textContent = data.online_teams;
    }
  });

  socket.on('auction_started', (data) => {
    console.log('[Host] Auction Started:', data);
    setLiveAuction(data);
    showToast(`Auction #${data.auction_id} started for ${data.category}`, 'info');
    clearBidFeed();
    disableStartButtons(true);
    if (statCurrentAuctionId) statCurrentAuctionId.textContent = `#${data.auction_id}`;
  });

  socket.on('bid_update', (data) => {
    console.log('[Host] Bid Update:', data);
    handleBidUpdate(data);
  });

  socket.on('auction_ended', (data) => {
    console.log('[Host] Auction Ended:', data);
    handleAuctionEnded(data);
  });

  socket.on('team_violation', (data) => {
    const strikeLabel = data.is_disqualified
      ? `DISQUALIFIED after 3 strikes`
      : `Strike ${data.strike_count}/3`;
    showToast(`🚨 Violation by Team ${data.team_code}: ${data.violation_type} — ${strikeLabel}`, 'danger', 7000);
    appendViolationRow(data);
    // Refresh teams table so DISQUALIFIED badge appears immediately
    refreshTeamsData();
  });

  socket.on('answer_result', (data) => {
    if (data.is_correct) {
      showToast(`🏆 Team ${data.team_code} answered CORRECTLY! Bounty +₹${parseFloat(data.reward_credited).toFixed(2)} credited.`, 'success', 5000);
    } else {
      showToast(`❌ Team ${data.team_code} answered WRONGLY. No bounty credited.`, 'warning', 5000);
    }
    refreshTeamsData();
  });

  // Timer logic - Total 40s Countdown (10s Reading -> 30s Bidding)
  function startTimer(endsAtIso, initialSeconds, biddingStartsAtIso) {
    if (timerInterval) clearInterval(timerInterval);
    const biddingStartsAt = biddingStartsAtIso ? new Date(biddingStartsAtIso).getTime() : null;
    const endsAt = endsAtIso ? new Date(endsAtIso).getTime() : Date.now() + ((initialSeconds || 40) * 1000);

    function tick() {
      const now = Date.now();
      const diffMs = endsAt - now;
      const totalSecLeft = Math.max(0, Math.ceil(diffMs / 1000));

      if (hostTimerDigits) {
        hostTimerDigits.textContent = totalSecLeft;
      }

      if (biddingStartsAt && now < biddingStartsAt) {
        const readingLeft = Math.max(0, Math.ceil((biddingStartsAt - now) / 1000));
        if (hostTimerBox) {
          hostTimerBox.classList.remove('warning');
          hostTimerBox.classList.add('reading-phase');
        }
        if (hostAuctionStatusBadge) {
          hostAuctionStatusBadge.textContent = '📖 READING (Bids open in ' + readingLeft + 's)';
          hostAuctionStatusBadge.style.background = 'var(--accent-cyan)';
        }
        return;
      }

      if (hostTimerBox) {
        hostTimerBox.classList.remove('reading-phase');
      }

      if (totalSecLeft <= 5 && totalSecLeft > 0) {
        hostTimerBox.classList.add('warning');
      } else {
        hostTimerBox.classList.remove('warning');
      }

      if (hostAuctionStatusBadge) {
        hostAuctionStatusBadge.textContent = '🔥 LIVE / BIDDING';
        hostAuctionStatusBadge.style.background = 'var(--accent-green)';
      }

      if (totalSecLeft <= 0) {
        clearInterval(timerInterval);
        if (hostTimerDigits) hostTimerDigits.textContent = '0';
        if (hostTimerBox) hostTimerBox.classList.remove('warning');
      }
    }

    tick();
    timerInterval = setInterval(tick, 200);
  }

  function setLiveAuction(data) {
    activeAuction = {
      ...data,
      id: data.id ?? data.auction_id
    };

    if (hostAuctionCard) hostAuctionCard.classList.add('active');
    if (hostNoAuction) hostNoAuction.style.display = 'none';
    if (hostActiveAuction) hostActiveAuction.style.display = 'block';

    if (hostAuctionStatusBadge) {
      hostAuctionStatusBadge.textContent = 'LIVE';
      hostAuctionStatusBadge.style.background = 'var(--accent-green)';
    }

    if (hostCategory) hostCategory.textContent = data.category || 'Mathematics';
    if (hostType) hostType.textContent = data.question_type || 'Standard';
    if (hostReward) hostReward.textContent = `₹${parseFloat(data.reward).toFixed(2)}`;
    if (hostQuestionText) hostQuestionText.textContent = data.question_text || '';

    // Handle question image
    if (data.question_image && hostImageContainer && hostQuestionImage) {
      hostQuestionImage.src = data.question_image;
      hostImageContainer.style.display = 'block';
    } else if (hostImageContainer) {
      hostImageContainer.style.display = 'none';
    }

    if (hostStartingBid) hostStartingBid.textContent = `₹${parseFloat(data.starting_bid).toFixed(2)}`;
    if (hostCurrentBid) hostCurrentBid.textContent = `₹${parseFloat(data.current_bid).toFixed(2)}`;
    if (statCurrentBid) statCurrentBid.textContent = `₹${parseFloat(data.current_bid).toFixed(2)}`;
    if (statCurrentAuctionId) statCurrentAuctionId.textContent = `#${data.id ?? data.auction_id}`;

    const leaderName = data.current_bidder_code ? `${data.current_bidder_code}` : 'No Bids';
    if (hostCurrentBidder) hostCurrentBidder.textContent = leaderName;
    if (statCurrentBidder) statCurrentBidder.textContent = leaderName;

    if (hostActiveAuctionId) hostActiveAuctionId.value = data.id ?? data.auction_id;

    startTimer(data.ends_at_iso, data.time_remaining || 40, data.bidding_starts_at_iso);
    disableStartButtons(true);
  }

  function setNoAuction() {
    activeAuction = null;
    if (timerInterval) clearInterval(timerInterval);

    if (hostAuctionCard) hostAuctionCard.classList.remove('active');
    if (hostNoAuction) hostNoAuction.style.display = 'block';
    if (hostActiveAuction) hostActiveAuction.style.display = 'none';

    if (hostAuctionStatusBadge) {
      hostAuctionStatusBadge.textContent = 'STANDBY / NO LIVE AUCTION';
      hostAuctionStatusBadge.style.background = 'var(--text-muted)';
    }

    if (hostCurrentBidder) hostCurrentBidder.textContent = 'No Bids';
    if (statCurrentBidder) statCurrentBidder.textContent = 'None';
    if (statCurrentAuctionId) statCurrentAuctionId.textContent = 'None';
    if (statCurrentBid) statCurrentBid.textContent = '₹0.00';

    disableStartButtons(false);
  }

  function handleBidUpdate(data) {
    if (hostCurrentBid) hostCurrentBid.textContent = `₹${parseFloat(data.current_bid).toFixed(2)}`;
    if (statCurrentBid) statCurrentBid.textContent = `₹${parseFloat(data.current_bid).toFixed(2)}`;

    const bidder = `${data.current_bidder_code} (${data.current_bidder_name})`;
    if (hostCurrentBidder) hostCurrentBidder.textContent = data.current_bidder_code;
    if (statCurrentBidder) statCurrentBidder.textContent = data.current_bidder_code;

    appendBidRow(data);
    startTimer(data.ends_at_iso, data.time_remaining || 40, data.bidding_starts_at_iso);
  }

  function handleAuctionEnded(data) {
    if (data.has_winner) {
      showToast(`🔨 Auction #${data.auction_id} SOLD to ${data.winner_team_code} for ₹${parseFloat(data.winning_bid).toFixed(2)}!`, 'success', 8000);
    } else {
      showToast(`Auction #${data.auction_id} closed with NO BIDS. Question returned to bank.`, 'info', 5000);
    }

    setNoAuction();
    refreshTeamsData();
  }

  function clearBidFeed() {
    if (hostBidsBody) {
      hostBidsBody.innerHTML = '<tr id="row-no-bids"><td colspan="3" style="text-align: center; color: var(--text-muted);">Auction opened. Awaiting first bid...</td></tr>';
    }
  }

  function appendBidRow(data) {
    if (!hostBidsBody) return;
    const noBidsRow = document.getElementById('row-no-bids');
    if (noBidsRow) noBidsRow.remove();

    const tr = document.createElement('tr');
    const timeStr = new Date().toTimeString().split(' ')[0];
    tr.innerHTML = `
      <td style="font-size: 0.8rem; color: var(--text-muted);">${timeStr}</td>
      <td style="font-weight: 600;">${data.current_bidder_code} <small>(${data.current_bidder_name})</small></td>
      <td style="color: #fbbf24; font-weight: 700;">₹${parseFloat(data.current_bid).toFixed(2)}</td>
    `;
    hostBidsBody.insertBefore(tr, hostBidsBody.firstChild);
  }

  function appendViolationRow(v) {
    if (!hostViolationsBody) return;
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td style="font-size: 0.8rem; color: var(--text-muted);">${v.occurred_at_formatted || 'Just now'}</td>
      <td style="font-weight: 600;">${v.team_code}</td>
      <td style="font-size: 0.8rem; color: var(--accent-red);">${v.violation_type}</td>
      <td>
        <span style="background: rgba(239,68,68,0.2); color: #f87171; font-weight: 700; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem;">
          Strike ${v.strike_count}/3
        </span>
      </td>
    `;
    hostViolationsBody.insertBefore(tr, hostViolationsBody.firstChild);
  }

  function disableStartButtons(disabled) {
    document.querySelectorAll('.btn-start-auction').forEach(btn => {
      btn.disabled = disabled;
      if (disabled) {
        btn.title = 'An auction is currently LIVE';
      } else {
        btn.removeAttribute('title');
      }
    });
  }

  async function refreshTeamsData() {
    try {
      const resp = await fetch('/api/host/state');
      const data = await resp.json();

      if (data.system_stats) {
        if (statRegisteredTeams) statRegisteredTeams.textContent = data.system_stats.registered_teams;
        if (statAvailableQuestions) statAvailableQuestions.textContent = data.system_stats.available_questions;
      }

      if (data.teams && hostTeamsBody) {
        let html = '';
        data.teams.forEach(t => {
          const strikesColor = t.violation_count >= 3 ? '#f87171'
            : t.violation_count >= 1 ? '#fbbf24'
            : 'var(--text-muted)';
          html += `
            <tr data-team-code="${t.team_code}" data-team-name="${t.team_name.toLowerCase()}">
              <td style="font-weight: 700;">
                ${t.team_code}
                <div style="font-size: 0.8rem; color: var(--text-muted); font-weight: normal;">${t.team_name}</div>
              </td>
              <td style="color: #34d399; font-weight: 700;">₹${parseFloat(t.current_balance).toFixed(2)}</td>
              <td>${t.questions_won}</td>
              <td>${t.questions_completed}/5</td>
              <td style="font-weight: 700; color: ${strikesColor};">${t.violation_count}/3</td>
              <td>
                ${!t.is_active ? '<span style="background: rgba(100,116,139,0.2); color: #94a3b8; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 700;">INACTIVE</span>' :
                  t.is_disqualified ? '<span style="background: rgba(239,68,68,0.2); color: #f87171; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 700;">DISQUALIFIED</span>' :
                  t.questions_completed >= 5 ? '<span style="background: rgba(59,130,246,0.2); color: #60a5fa; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 700;">COMPLETED</span>' :
                  `<span style="background: rgba(16,185,129,0.2); color: #34d399; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 700;">${t.status}</span>`
                }
              </td>
            </tr>
          `;
        });
        hostTeamsBody.innerHTML = html;
      }
    } catch (e) {
      console.error('Error refreshing host team data:', e);
    }
  }

  // Bind toggle active buttons
  function bindToggleButtons() {
    document.querySelectorAll('.btn-toggle-active').forEach(btn => {
      btn.onclick = async () => {
        const teamId = btn.getAttribute('data-team-id');
        try {
          const resp = await fetch('/api/host/teams/toggle-active', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ team_id: teamId })
          });
          const res = await resp.json();
          if (res.success) {
            showToast(res.message, 'info');
            refreshTeamsData();
          } else {
            showToast(res.error, 'danger');
          }
        } catch (err) {
          showToast('Failed to toggle team state.', 'danger');
        }
      };
    });
  }
  bindToggleButtons();

  // Search filter for teams table
  if (inputSearchTeams) {
    inputSearchTeams.addEventListener('input', () => {
      const q = inputSearchTeams.value.trim().toLowerCase();
      document.querySelectorAll('#host-teams-body tr').forEach(row => {
        const code = row.getAttribute('data-team-code') || '';
        const name = row.getAttribute('data-team-name') || '';
        if (code.toLowerCase().includes(q) || name.includes(q)) {
          row.style.display = '';
        } else {
          row.style.display = 'none';
        }
      });
    });
  }

  // Add Team Modal Handlers
  if (btnOpenAddTeamModal && modalAddTeam) {
    btnOpenAddTeamModal.addEventListener('click', () => {
      modalAddTeam.style.display = 'flex';
      addTeamErrorMsg.style.display = 'none';
      addTeamSuccessMsg.style.display = 'none';
      if (addTeamName) addTeamName.value = '';
      if (addTeamCode) addTeamCode.value = '';
      if (addTeamPassword) addTeamPassword.value = '';
    });
  }

  function closeAddTeamModal() {
    if (modalAddTeam) modalAddTeam.style.display = 'none';
  }

  if (btnCloseAddTeamModal) btnCloseAddTeamModal.addEventListener('click', closeAddTeamModal);
  if (btnCancelAddTeam) btnCancelAddTeam.addEventListener('click', closeAddTeamModal);

  if (btnSubmitAddTeam) {
    btnSubmitAddTeam.addEventListener('click', async () => {
      const name = addTeamName.value.trim();
      const code = addTeamCode.value.trim().toUpperCase();
      const pwd = addTeamPassword.value.trim();
      const balance = parseFloat(addTeamBalance.value) || 10000.0;

      if (!name || !code || !pwd) {
        addTeamErrorMsg.textContent = 'Please fill in Team Name, Team Code, and Password.';
        addTeamErrorMsg.style.display = 'block';
        return;
      }

      btnSubmitAddTeam.disabled = true;
      try {
        const resp = await fetch('/api/host/teams/add', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            team_name: name,
            team_code: code,
            password: pwd,
            starting_balance: balance
          })
        });
        const res = await resp.json();
        if (res.success) {
          addTeamSuccessMsg.textContent = res.message;
          addTeamSuccessMsg.style.display = 'block';
          addTeamErrorMsg.style.display = 'none';
          showToast(res.message, 'success');
          setTimeout(() => {
            closeAddTeamModal();
            refreshTeamsData();
          }, 1200);
        } else {
          addTeamErrorMsg.textContent = res.error || 'Failed to add team.';
          addTeamErrorMsg.style.display = 'block';
        }
      } catch (err) {
        addTeamErrorMsg.textContent = 'Network error adding team.';
        addTeamErrorMsg.style.display = 'block';
      } finally {
        btnSubmitAddTeam.disabled = false;
      }
    });
  }

  // Reset Test Data Handler
  if (btnResetTestData) {
    btnResetTestData.addEventListener('click', async () => {
      const confirmPrompt = prompt(
        '⚠️ RESET TEST DATA: This will clear all active auctions, bids, and submissions, and reset all team purses to ₹10,000.\n\nType RESET to confirm:'
      );
      if (confirmPrompt !== 'RESET') {
        showToast('Reset cancelled.', 'info');
        return;
      }

      btnResetTestData.disabled = true;
      try {
        const resp = await fetch('/api/host/reset-test-data', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        const res = await resp.json();
        if (res.success) {
          showToast(res.message, 'success', 6000);
          setNoAuction();
          setTimeout(() => window.location.reload(), 1500);
        } else {
          showToast(res.error, 'danger');
        }
      } catch (err) {
        showToast('Error resetting test data.', 'danger');
      } finally {
        btnResetTestData.disabled = false;
      }
    });
  }

  // Button actions: Start Auction (Delegated event listener)
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('.btn-start-auction');
    if (!btn) return;
    const qId = btn.getAttribute('data-question-id');
    if (!qId) return;

    btn.disabled = true;
    const originalText = btn.innerHTML;
    btn.innerHTML = '⏳ Launching...';

    try {
      const resp = await fetch('/api/host/start-auction', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question_id: qId })
      });
      const res = await resp.json();
      if (res.success) {
        showToast(res.message, 'success');
      } else {
        showToast(`Error: ${res.error}`, 'danger');
        btn.disabled = false;
        btn.innerHTML = originalText;
      }
    } catch (err) {
      console.error('Network error starting auction:', err);
      showToast('Network error starting auction.', 'danger');
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
  });

  // Cancel Auction
  if (btnCancelAuction) {
    btnCancelAuction.addEventListener('click', async () => {
      if (!confirm('Are you sure you want to cancel the active auction without penalty?')) return;
      const auctionId = hostActiveAuctionId.value;
      try {
        const resp = await fetch('/api/host/cancel-auction', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ auction_id: auctionId })
        });
        const res = await resp.json();
        if (res.success) {
          showToast(res.message, 'warning');
          setNoAuction();
        } else {
          showToast(res.error, 'danger');
        }
      } catch (err) {
        showToast('Error cancelling auction.', 'danger');
      }
    });
  }

  // End Auction (Force close)
  if (btnEndAuction) {
    btnEndAuction.addEventListener('click', async () => {
      if (!confirm('Finalize and end auction now?')) return;
      const auctionId = hostActiveAuctionId.value;
      try {
        const resp = await fetch('/api/host/end-auction', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ auction_id: auctionId })
        });
        const res = await resp.json();
        if (res.success) {
          showToast(res.message, 'info');
        } else {
          showToast(res.error, 'danger');
        }
      } catch (err) {
        showToast('Error ending auction.', 'danger');
      }
    });
  }

  // ==========================================
  // QUESTION PHOTO UPLOAD (JPEG / PNG)
  // ==========================================
  document.querySelectorAll('.input-upload-image').forEach(input => {
    input.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      const qId = e.target.getAttribute('data-question-id');
      const formData = new FormData();
      formData.append('question_id', qId);
      formData.append('image', file);

      showToast(`Uploading photo for Question #${qId}...`, 'info');

      try {
        const resp = await fetch('/api/host/questions/upload-image', {
          method: 'POST',
          body: formData
        });
        const res = await resp.json();
        if (res.success) {
          showToast(res.message, 'success');
          // Update thumbnail in table
          const imgWrap = document.getElementById(`q-img-wrap-${qId}`);
          if (imgWrap) {
            imgWrap.innerHTML = `
              <div style="margin-bottom: 0.25rem;">
                <a href="${res.image_url}" target="_blank">
                  <img src="${res.image_url}" alt="Q${qId}" style="height: 36px; max-width: 55px; object-fit: contain; border-radius: 4px; border: 1px solid var(--border-color);">
                </a>
              </div>
            `;
          }
          const btnLabel = document.getElementById(`q-img-btn-label-${qId}`);
          if (btnLabel) btnLabel.textContent = 'Change';

          // If this question is currently LIVE, update live monitor immediately
          if (activeAuction && String(activeAuction.question_id) === String(qId)) {
            if (hostQuestionImage && hostImageContainer) {
              hostQuestionImage.src = res.image_url;
              hostImageContainer.style.display = 'block';
            }
          }
        } else {
          showToast(`Upload failed: ${res.error}`, 'danger');
        }
      } catch (err) {
        console.error('Upload error:', err);
        showToast('Network error uploading image.', 'danger');
      }
    });
  });

  // ==========================================
  // ADD QUESTION MODAL LOGIC
  // ==========================================
  const modalAddQuestion = document.getElementById('modal-add-question');
  const btnOpenAddQuestionModal = document.getElementById('btn-open-add-question-modal');
  const btnCloseAddQuestionModal = document.getElementById('btn-close-add-question-modal');
  const btnCancelAddQuestion = document.getElementById('btn-cancel-add-question');
  const btnSubmitAddQuestion = document.getElementById('btn-submit-add-question');

  const addQCategory = document.getElementById('add-q-category');
  const addQText = document.getElementById('add-q-text');
  const addQFile = document.getElementById('add-q-file');
  const addQType = document.getElementById('add-q-type');
  const addQAnswer = document.getElementById('add-q-answer');
  const addQStartBid = document.getElementById('add-q-start-bid');
  const addQReward = document.getElementById('add-q-reward');
  const addQErrorMsg = document.getElementById('add-q-error-msg');
  const addQSuccessMsg = document.getElementById('add-q-success-msg');

  function openAddQuestionModal() {
    if (!modalAddQuestion) return;
    addQErrorMsg.style.display = 'none';
    addQSuccessMsg.style.display = 'none';
    modalAddQuestion.style.display = 'flex';
  }

  function closeAddQuestionModal() {
    if (!modalAddQuestion) return;
    modalAddQuestion.style.display = 'none';
    if (document.getElementById('form-add-question')) {
      document.getElementById('form-add-question').reset();
    }
  }

  if (btnOpenAddQuestionModal) btnOpenAddQuestionModal.addEventListener('click', openAddQuestionModal);
  if (btnCloseAddQuestionModal) btnCloseAddQuestionModal.addEventListener('click', closeAddQuestionModal);
  if (btnCancelAddQuestion) btnCancelAddQuestion.addEventListener('click', closeAddQuestionModal);

  if (btnSubmitAddQuestion) {
    btnSubmitAddQuestion.addEventListener('click', async () => {
      const category = addQCategory.value.trim();
      const text = addQText.value.trim();
      const answer = addQAnswer.value.trim();
      const qtype = addQType.value;
      const startBid = parseFloat(addQStartBid.value) || 500;
      const reward = parseFloat(addQReward.value) || 2000;

      addQErrorMsg.style.display = 'none';
      addQSuccessMsg.style.display = 'none';

      if (!category) {
        addQErrorMsg.textContent = 'Please enter a category.';
        addQErrorMsg.style.display = 'block';
        return;
      }
      if (!text) {
        addQErrorMsg.textContent = 'Please enter question description.';
        addQErrorMsg.style.display = 'block';
        return;
      }
      if (!answer) {
        addQErrorMsg.textContent = 'Please enter the correct answer.';
        addQErrorMsg.style.display = 'block';
        return;
      }

      const formData = new FormData();
      formData.append('category', category);
      formData.append('question_text', text);
      formData.append('question_type', qtype);
      formData.append('correct_answer', answer);
      formData.append('starting_bid', startBid);
      formData.append('reward', reward);

      if (addQFile && addQFile.files[0]) {
        formData.append('image', addQFile.files[0]);
      }

      btnSubmitAddQuestion.disabled = true;
      btnSubmitAddQuestion.textContent = 'Saving...';

      try {
        const resp = await fetch('/api/host/questions/add', {
          method: 'POST',
          body: formData
        });
        const res = await resp.json();
        if (res.success) {
          addQSuccessMsg.textContent = res.message;
          addQSuccessMsg.style.display = 'block';
          showToast(res.message, 'success');
          setTimeout(() => {
            closeAddQuestionModal();
            window.location.reload();
          }, 1000);
        } else {
          addQErrorMsg.textContent = res.error || 'Failed to add question.';
          addQErrorMsg.style.display = 'block';
          btnSubmitAddQuestion.disabled = false;
          btnSubmitAddQuestion.textContent = 'Save Question';
        }
      } catch (err) {
        console.error('Error adding question:', err);
        addQErrorMsg.textContent = 'Network error while adding question.';
        addQErrorMsg.style.display = 'block';
        btnSubmitAddQuestion.disabled = false;
        btnSubmitAddQuestion.textContent = 'Save Question';
      }
    });
  }
});
