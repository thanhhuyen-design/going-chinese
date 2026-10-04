/**
 * app.js - Xử lý hàng trăm ảnh song song, chống trùng lặp, OCR khung đen, Pinyin Unicode và dịch tiếng Việt.
 */

// Global State
const state = {
  queue: [],               // Danh sách tất cả file ảnh đã tải lên
  isProcessing: false,     // Trạng thái đang chạy
  concurrency: 4,          // Số lượng ảnh xử lý song song cùng lúc
  vocabMap: new Map(),     // Map<hanzi, { hanzi, pinyin, meaning, count, conf, review, crops }>
  startTime: null,
  timerInterval: null,
  processedCount: 0,
  activeWorkers: 0,
};

// DOM Elements
const elements = {
  dropzone: document.getElementById('dropzone'),
  fileInput: document.getElementById('fileInput'),
  btnBrowse: document.getElementById('btnBrowse'),
  statusBadge: document.getElementById('statusBadge'),
  timerText: document.getElementById('timerText'),
  progressPercent: document.getElementById('progressPercent'),
  progressBar: document.getElementById('progressBar'),
  statTotal: document.getElementById('statTotal'),
  statDone: document.getElementById('statDone'),
  statWords: document.getElementById('statWords'),
  statUnique: document.getElementById('statUnique'),
  selectedCountBadge: document.getElementById('selectedCountBadge'),
  queueList: document.getElementById('queueList'),
  btnRetryAllFailed: document.getElementById('btnRetryAllFailed'),
  vocabBox: document.getElementById('vocabBox'),
  metaCount: document.getElementById('metaCount'),
  qualityTableBody: document.getElementById('qualityTableBody'),
  reviewAlertBadge: document.getElementById('reviewAlertBadge'),
  btnCopyAll: document.getElementById('btnCopyAll'),
  btnDownloadTxt: document.getElementById('btnDownloadTxt'),
  btnDownloadCsv: document.getElementById('btnDownloadCsv'),
  btnClearAll: document.getElementById('btnClearAll'),
  btnTryDemo: document.getElementById('btnTryDemo'),
  imageModal: document.getElementById('imageModal'),
  modalImg: document.getElementById('modalImg'),
  modalTitle: document.getElementById('modalTitle'),
  toastContainer: document.getElementById('toastContainer'),
  concurrencySelect: document.getElementById('concurrencySelect'),
  formatSelect: document.getElementById('formatSelect'),
  sortSelect: document.getElementById('sortSelect'),
  vocabSearchInput: document.getElementById('vocabSearchInput')
};

// Initialize Event Listeners
function init() {
  // File Browse
  elements.btnBrowse.addEventListener('click', () => elements.fileInput.click());
  elements.fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(Array.from(e.target.files));
      elements.fileInput.value = ''; // Reset để có thể chọn lại cùng file
    }
  });

  // Drag and Drop
  ['dragenter', 'dragover'].forEach(eventName => {
    elements.dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      elements.dropzone.classList.add('drag-over');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    elements.dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      elements.dropzone.classList.remove('drag-over');
    });
  });

  elements.dropzone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    if (dt && dt.files && dt.files.length > 0) {
      const imgFiles = Array.from(dt.files).filter(f => f.type.startsWith('image/'));
      if (imgFiles.length > 0) {
        handleFiles(imgFiles);
      } else {
        showToast('Vui lòng chỉ thả các file hình ảnh (.png, .jpg, .webp...)', 'warning');
      }
    }
  });

  // Window drag prevention
  window.addEventListener('dragover', (e) => e.preventDefault());
  window.addEventListener('drop', (e) => e.preventDefault());

  // Actions
  elements.btnCopyAll.addEventListener('click', copyVocabularyList);
  elements.btnDownloadTxt.addEventListener('click', downloadTxtFile);
  elements.btnDownloadCsv.addEventListener('click', downloadCsvFile);
  elements.btnClearAll.addEventListener('click', clearAll);
  elements.btnTryDemo.addEventListener('click', loadAllDemoSamples);
  elements.btnRetryAllFailed.addEventListener('click', retryFailedItems);

  if (elements.concurrencySelect) {
    elements.concurrencySelect.addEventListener('change', (e) => {
      state.concurrency = parseInt(e.target.value) || 4;
      showToast(`Đã thiết lập ${state.concurrency} luồng xử lý song song`, 'info');
    });
  }

  if (elements.formatSelect) {
    elements.formatSelect.addEventListener('change', () => renderVocabularyList());
  }

  if (elements.sortSelect) {
    elements.sortSelect.addEventListener('change', () => renderVocabularyList());
  }

  if (elements.vocabSearchInput) {
    elements.vocabSearchInput.addEventListener('input', () => {
      renderVocabularyList();
      renderQualityTable();
    });
  }
}

// Thêm file vào hàng đợi (Append mode - không mất danh sách cũ)
function handleFiles(newFiles) {
  if (!newFiles || newFiles.length === 0) return;

  const addedItems = [];
  newFiles.forEach(file => {
    const item = {
      id: 'img_' + Math.random().toString(36).substr(2, 9),
      file: file,
      filename: file.name,
      size: file.size,
      status: 'pending', // pending, processing, success, error, no_boxes
      errorMsg: null,
      words: []
    };
    state.queue.push(item);
    addedItems.push(item);
  });

  elements.selectedCountBadge.innerText = `${state.queue.length} ảnh trong danh sách`;
  updateStats();
  renderQueue();
  showToast(`Đã thêm ${newFiles.length} ảnh vào hàng đợi xử lý`, 'info');

  // Bắt đầu xử lý song song nếu chưa chạy
  startBatchProcessing();
}

// Bắt đầu xử lý hàng loạt song song
function startBatchProcessing() {
  if (state.isProcessing) return;

  const pendingItems = state.queue.filter(i => i.status === 'pending');
  if (pendingItems.length === 0) return;

  state.isProcessing = true;
  if (!state.startTime) {
    state.startTime = Date.now();
  }

  elements.statusBadge.className = 'status-badge processing';
  elements.statusBadge.innerText = 'Đang xử lý...';

  // Chạy timer
  if (state.timerInterval) clearInterval(state.timerInterval);
  state.timerInterval = setInterval(() => {
    const elapsedSec = ((Date.now() - state.startTime) / 1000).toFixed(1);
    elements.timerText.innerText = `${elapsedSec}s`;
  }, 100);

  // Khởi động các worker xử lý song song
  for (let i = 0; i < state.concurrency; i++) {
    dispatchNextWorker();
  }
}

// Điều phối worker nhận việc tiếp theo từ hàng đợi
function dispatchNextWorker() {
  // Tìm item pending tiếp theo
  const nextItem = state.queue.find(i => i.status === 'pending');
  if (!nextItem) {
    checkCompletion();
    return;
  }

  nextItem.status = 'processing';
  state.activeWorkers++;
  updateItemInQueueUI(nextItem);
  updateStats();

  processSingleImageFile(nextItem)
    .then(result => {
      handleItemSuccess(nextItem, result);
    })
    .catch(err => {
      handleItemError(nextItem, err);
    })
    .finally(() => {
      state.activeWorkers--;
      dispatchNextWorker(); // Lấy việc tiếp theo
    });
}

// Gọi API xử lý ảnh
async function processSingleImageFile(item) {
  const formData = new FormData();
  formData.append('file', item.file, item.filename);

  const response = await fetch('/api/process-image', {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new Error(errData.message || `Lỗi máy chủ (${response.status})`);
  }

  return await response.json();
}

// Xử lý khi nhận diện thành công 1 ảnh
function handleItemSuccess(item, result) {
  item.status = result.words && result.words.length > 0 ? 'success' : 'no_boxes';
  item.words = result.words || [];

  // Đưa các từ vào hệ thống và chống trùng lặp (Deduplication)
  item.words.forEach(w => {
    const key = w.hanzi.trim();
    if (!key) return;

    if (state.vocabMap.has(key)) {
      // Đã có từ này -> Cập nhật số lần xuất hiện
      const existing = state.vocabMap.get(key);
      existing.count = (existing.count || 1) + 1;
      if (w.crop_preview && !existing.crops.includes(w.crop_preview)) {
        existing.crops.push(w.crop_preview);
      }
    } else {
      // Từ mới -> Lưu vào Map
      state.vocabMap.set(key, {
        id: w.id,
        hanzi: key,
        pinyin: w.pinyin,
        meaning: w.meaning,
        confidence: w.confidence,
        needs_review: w.needs_review,
        crops: w.crop_preview ? [w.crop_preview] : [],
        count: 1
      });
    }
  });

  updateItemInQueueUI(item);
  updateStats();
  renderVocabularyList();
  renderQualityTable();
}

// Xử lý khi 1 ảnh bị lỗi (không dừng các ảnh khác)
function handleItemError(item, error) {
  item.status = 'error';
  item.errorMsg = error.message || 'Lỗi không xác định';
  updateItemInQueueUI(item);
  updateStats();
  elements.btnRetryAllFailed.style.display = 'inline-flex';
}

// Kiểm tra toàn bộ tiến trình đã hoàn thành chưa
function checkCompletion() {
  if (state.activeWorkers === 0) {
    const anyPending = state.queue.some(i => i.status === 'pending');
    if (!anyPending) {
      state.isProcessing = false;
      if (state.timerInterval) {
        clearInterval(state.timerInterval);
        state.timerInterval = null;
      }
      elements.statusBadge.className = 'status-badge completed';
      elements.statusBadge.innerText = 'Completed (Hoàn thành)';
      
      const totalWords = Array.from(state.vocabMap.values()).reduce((sum, v) => sum + v.count, 0);
      showToast(`Xử lý xong! Tìm thấy ${totalWords} lượt từ (${state.vocabMap.size} từ duy nhất)`, 'success');
    }
  }
}

// Cập nhật thống kê và thanh tiến trình
function updateStats() {
  const total = state.queue.length;
  const done = state.queue.filter(i => i.status === 'success' || i.status === 'no_boxes' || i.status === 'error').length;
  const percent = total > 0 ? Math.round((done / total) * 100) : 0;

  elements.statTotal.innerText = total;
  elements.statDone.innerText = done;
  elements.statWords.innerText = Array.from(state.vocabMap.values()).reduce((sum, v) => sum + v.count, 0);
  elements.statUnique.innerText = state.vocabMap.size;

  elements.progressPercent.innerText = `${percent}%`;
  elements.progressBar.style.width = `${percent}%`;

  if (state.isProcessing) {
    elements.statusBadge.innerText = `Đang xử lý (${done}/${total})...`;
  }
}

// Hiển thị danh sách ảnh tải lên
function renderQueue() {
  if (state.queue.length === 0) {
    elements.queueList.innerHTML = `
      <div style="text-align: center; color: var(--slate-400); font-size: 13px; padding: 24px 0;">
        Chưa có ảnh nào trong hàng đợi
      </div>
    `;
    return;
  }

  // Để tránh quá tải DOM khi có 500 ảnh, chỉ hiển thị tối đa 50 item gần nhất hoặc phân trang
  const displayItems = state.queue.slice(-60);
  elements.queueList.innerHTML = displayItems.map(item => `
    <div class="queue-item ${item.status}" id="qitem_${item.id}">
      <div class="queue-item-info">
        <span style="font-size: 16px;">
          ${getStatusIcon(item.status)}
        </span>
        <div>
          <div class="queue-filename" title="${item.filename}">${item.filename}</div>
          <div style="font-size: 11px; color: var(--slate-500);">
            ${getStatusDescription(item)}
          </div>
        </div>
      </div>
      <div>
        ${item.status === 'error' ? `
          <button class="btn btn-outline btn-sm" onclick="retrySingleItem('${item.id}')" title="Thử lại ảnh này">
            🔄 Thử lại
          </button>
        ` : ''}
      </div>
    </div>
  `).join('');
}

// Cập nhật trạng thái của 1 item cụ thể trong UI để không render lại cả list
function updateItemInQueueUI(item) {
  const el = document.getElementById(`qitem_${item.id}`);
  if (!el) return;
  el.className = `queue-item ${item.status}`;
  el.querySelector('.queue-filename').nextElementSibling.innerHTML = getStatusDescription(item);
  el.querySelector('.queue-item-info span').innerHTML = getStatusIcon(item.status);
}

function getStatusIcon(status) {
  switch (status) {
    case 'pending': return '⏳';
    case 'processing': return '⚙️';
    case 'success': return '✅';
    case 'no_boxes': return 'ℹ️';
    case 'error': return '❌';
    default: return '📄';
  }
}

function getStatusDescription(item) {
  switch (item.status) {
    case 'pending': return 'Đang đợi trong hàng đợi...';
    case 'processing': return 'Đang nhận diện khung đen & OCR...';
    case 'success': return `Tìm thấy ${item.words.length} từ trong khung`;
    case 'no_boxes': return 'Không có khung màu đen hợp lệ';
    case 'error': return `<span style="color:#EF4444;">${item.errorMsg}</span>`;
    default: return '';
  }
}

// Thử lại 1 ảnh bị lỗi
window.retrySingleItem = function(id) {
  const item = state.queue.find(i => i.id === id);
  if (!item) return;
  item.status = 'pending';
  item.errorMsg = null;
  updateItemInQueueUI(item);
  updateStats();
  startBatchProcessing();
};

// Thử lại tất cả ảnh lỗi
function retryFailedItems() {
  const failed = state.queue.filter(i => i.status === 'error');
  if (failed.length === 0) return;
  failed.forEach(item => {
    item.status = 'pending';
    item.errorMsg = null;
  });
  renderQueue();
  updateStats();
  elements.btnRetryAllFailed.style.display = 'none';
  startBatchProcessing();
}

// HIỂN THỊ KẾT QUẢ ĐẦU RA VOCABULARY LIST (MỤC QUAN TRỌNG NHẤT)
// Format chuẩn mặc định: Pinyin — Nghĩa tiếng Việt
function renderVocabularyList() {
  let items = Array.from(state.vocabMap.values());
  elements.metaCount.innerText = items.length;

  if (items.length === 0) {
    elements.vocabBox.innerText = '';
    return;
  }

  // Lọc theo từ khóa tìm kiếm nếu có
  const query = elements.vocabSearchInput ? elements.vocabSearchInput.value.trim().toLowerCase() : '';
  if (query) {
    items = items.filter(it => 
      (it.pinyin && it.pinyin.toLowerCase().includes(query)) ||
      (it.hanzi && it.hanzi.toLowerCase().includes(query)) ||
      (it.meaning && it.meaning.toLowerCase().includes(query))
    );
  }

  // Sắp xếp
  const sortMode = elements.sortSelect ? elements.sortSelect.value : 'az';
  if (sortMode === 'freq') {
    items.sort((a, b) => (b.count || 1) - (a.count || 1));
  } else {
    items.sort((a, b) => (a.pinyin || '').localeCompare(b.pinyin || ''));
  }

  // Định dạng hiển thị
  const formatMode = elements.formatSelect ? elements.formatSelect.value : 'pinyin_meaning';
  const lines = items.map(item => {
    const pinyin = item.pinyin || '';
    const meaning = item.meaning || '';
    const hanzi = item.hanzi || '';
    
    if (formatMode === 'hanzi_pinyin_meaning') {
      return `${hanzi} — ${pinyin} — ${meaning}`;
    }
    // Mặc định chuẩn xác theo yêu cầu: Pinyin — Nghĩa tiếng Việt
    return `${pinyin} — ${meaning}`;
  });

  elements.vocabBox.innerText = lines.join('\n');
}

// HIỂN THỊ BẢNG KIỂM TRA CHẤT LƯỢNG (HUMAN-IN-THE-LOOP)
function renderQualityTable() {
  let items = Array.from(state.vocabMap.values());
  if (items.length === 0) {
    elements.qualityTableBody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align: center; color: var(--slate-400); padding: 32px 0;">
          Chưa có từ nào để kiểm tra
        </td>
      </tr>
    `;
    elements.reviewAlertBadge.style.display = 'none';
    return;
  }

  // Lọc theo tìm kiếm
  const query = elements.vocabSearchInput ? elements.vocabSearchInput.value.trim().toLowerCase() : '';
  if (query) {
    items = items.filter(it => 
      (it.pinyin && it.pinyin.toLowerCase().includes(query)) ||
      (it.hanzi && it.hanzi.toLowerCase().includes(query)) ||
      (it.meaning && it.meaning.toLowerCase().includes(query))
    );
  }

  let hasWarning = false;
  elements.qualityTableBody.innerHTML = items.map(item => {
    const isWarn = item.needs_review || (item.confidence && item.confidence < 0.85);
    if (isWarn) hasWarning = true;
    const cropImg = item.crops && item.crops.length > 0 ? item.crops[0] : '';

    return `
      <tr id="row_${item.id}">
        <td>
          ${cropImg ? `
            <img src="${cropImg}" class="crop-preview-thumb" onclick="openModal('${cropImg}', '${escapeHtml(item.hanzi)}')" title="Bấm để phóng to khung đen gốc">
          ` : `<span style="color:var(--slate-400);font-size:11px;">Không có ảnh</span>`}
        </td>
        <td>
          <input type="text" class="hanzi-edit-input" value="${escapeHtml(item.hanzi)}" 
            onchange="onHanziEdit('${escapeHtml(item.hanzi)}', this.value)" 
            title="Sửa chữ Hán nếu OCR nhận diện nhầm">
        </td>
        <td>
          <span class="pinyin-display" id="pinyin_${escapeHtml(item.hanzi)}">${escapeHtml(item.pinyin)}</span>
        </td>
        <td>
          <input type="text" class="meaning-edit-input" value="${escapeHtml(item.meaning)}" 
            onchange="onMeaningEdit('${escapeHtml(item.hanzi)}', this.value)" 
            title="Chỉnh sửa nghĩa tiếng Việt">
        </td>
        <td style="text-align: center;">
          <button class="audio-btn" onclick="speakChinese('${escapeHtml(item.hanzi)}')" title="Nghe phát âm chuẩn">
            🔊
          </button>
        </td>
        <td style="text-align: center;">
          <span class="review-badge ${isWarn ? 'warning' : 'good'}">
            ${isWarn ? '⚠️ Cần xem' : '✓ Tốt'} (${Math.round((item.confidence || 0.95) * 100)}%)
          </span>
        </td>
      </tr>
    `;
  }).join('');

  elements.reviewAlertBadge.style.display = hasWarning ? 'inline-flex' : 'none';
}

// Xử lý khi người dùng sửa chữ Hán trực tiếp trong bảng
window.onHanziEdit = async function(oldHanzi, newHanzi) {
  newHanzi = newHanzi.trim();
  if (!newHanzi || newHanzi === oldHanzi) return;

  const item = state.vocabMap.get(oldHanzi);
  if (!item) return;

  try {
    showToast(`Đang cập nhật Pinyin & nghĩa cho "${newHanzi}"...`, 'info');
    const res = await fetch('/api/retranslate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hanzi: newHanzi })
    });
    const data = await res.json();

    // Xóa key cũ, thêm key mới vào vocabMap
    state.vocabMap.delete(oldHanzi);
    item.hanzi = newHanzi;
    item.pinyin = data.pinyin;
    item.meaning = data.meaning;
    item.needs_review = false;
    state.vocabMap.set(newHanzi, item);

    // Cập nhật lại UI
    renderVocabularyList();
    renderQualityTable();
    showToast(`Đã cập nhật: ${data.pinyin} — ${data.meaning}`, 'success');
  } catch (err) {
    showToast('Lỗi khi cập nhật từ vựng: ' + err.message, 'error');
  }
};

// Xử lý khi người dùng chỉnh sửa nghĩa tiếng Việt
window.onMeaningEdit = async function(hanzi, newMeaning) {
  newMeaning = newMeaning.trim();
  if (!newMeaning) return;

  const item = state.vocabMap.get(hanzi);
  if (item) {
    item.meaning = newMeaning;
    renderVocabularyList();
    // Lưu vào backend cache
    fetch('/api/update-meaning', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hanzi: hanzi, meaning: newMeaning })
    }).catch(() => {});
  }
};

// Phát âm tiếng Trung bằng Web Speech API
window.speakChinese = function(text) {
  if (!('speechSynthesis' in window)) {
    showToast('Trình duyệt không hỗ trợ phát âm âm thanh', 'warning');
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'zh-CN';
  utterance.rate = 0.85;
  window.speechSynthesis.speak(utterance);
};

// Copy all vào Clipboard
function copyVocabularyList() {
  const text = elements.vocabBox.innerText;
  if (!text || text.trim() === '') {
    showToast('Chưa có từ vựng nào để sao chép', 'warning');
    return;
  }

  navigator.clipboard.writeText(text).then(() => {
    showToast('✓ Đã sao chép toàn bộ danh sách vào Clipboard!', 'success');
  }).catch(() => {
    // Fallback cho trình duyệt cũ
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    showToast('✓ Đã sao chép toàn bộ danh sách vào Clipboard!', 'success');
  });
}

// Download file .txt
function downloadTxtFile() {
  const text = elements.vocabBox.innerText;
  if (!text || text.trim() === '') {
    showToast('Chưa có từ vựng nào để tải xuống', 'warning');
    return;
  }

  // Thêm UTF-8 BOM (\uFEFF) để file mở bằng Notepad trên Windows không bị lỗi font tiếng Việt và Pinyin
  const blob = new Blob(['\uFEFF' + text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `chinese_vocab_${new Date().toISOString().slice(0, 10)}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast('✓ Đã tải xuống file .txt thành công', 'success');
}

// Download file .csv
function downloadCsvFile() {
  const items = Array.from(state.vocabMap.values());
  if (items.length === 0) {
    showToast('Chưa có từ vựng nào để tải xuống', 'warning');
    return;
  }

  items.sort((a, b) => a.pinyin.localeCompare(b.pinyin));
  let csvContent = '\uFEFF"Hán Tự","Pinyin","Nghĩa Tiếng Việt","Số Lần Xuất Hiện"\n';
  items.forEach(item => {
    const hanzi = `"${(item.hanzi || '').replace(/"/g, '""')}"`;
    const pinyin = `"${(item.pinyin || '').replace(/"/g, '""')}"`;
    const meaning = `"${(item.meaning || '').replace(/"/g, '""')}"`;
    const count = item.count || 1;
    csvContent += `${hanzi},${pinyin},${meaning},${count}\n`;
  });

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `chinese_vocab_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast('✓ Đã tải xuống file .csv (dùng cho Anki, Excel) thành công', 'success');
}

// Xóa tất cả dữ liệu làm mới
function clearAll() {
  if (state.queue.length > 0 && !confirm('Bạn có chắc muốn xóa toàn bộ ảnh và danh sách từ vựng hiện tại?')) {
    return;
  }
  state.queue = [];
  state.vocabMap.clear();
  state.isProcessing = false;
  state.startTime = null;
  if (state.timerInterval) clearInterval(state.timerInterval);

  elements.selectedCountBadge.innerText = '0 ảnh đã chọn';
  elements.statusBadge.className = 'status-badge idle';
  elements.statusBadge.innerText = 'Chờ tải ảnh';
  elements.timerText.innerText = '0.0s';
  elements.btnRetryAllFailed.style.display = 'none';

  updateStats();
  renderQueue();
  renderVocabularyList();
  renderQualityTable();
  showToast('Đã xóa sạch dữ liệu', 'info');
}

// Thử nghiệm tải ảnh mẫu demo có sẵn
window.loadDemoSample = async function(filename) {
  try {
    showToast(`Đang nạp ảnh mẫu: ${filename}...`, 'info');
    const resp = await fetch(`/static/test_samples/${filename}`);
    if (!resp.ok) throw new Error('Không tải được ảnh mẫu');
    const blob = await resp.blob();
    const file = new File([blob], filename, { type: 'image/png' });
    handleFiles([file]);
  } catch (err) {
    showToast('Lỗi nạp ảnh mẫu: ' + err.message, 'error');
  }
};

window.loadAllDemoSamples = async function() {
  try {
    showToast('Đang nạp cùng lúc 3 trang bài học mẫu...', 'info');
    const samples = ['sample_lesson_01.png', 'sample_lesson_02.png', 'sample_lesson_03.png'];
    const files = [];
    for (const name of samples) {
      const resp = await fetch(`/static/test_samples/${name}`);
      if (resp.ok) {
        const blob = await resp.blob();
        files.push(new File([blob], name, { type: 'image/png' }));
      }
    }
    if (files.length > 0) {
      handleFiles(files);
    }
  } catch (err) {
    showToast('Lỗi: ' + err.message, 'error');
  }
};

// Modal xem ảnh cắt phóng to
window.openModal = function(src, title) {
  elements.modalImg.src = src;
  elements.modalTitle.innerText = `Vùng khung đen: ${title}`;
  elements.imageModal.style.display = 'flex';
};

window.closeModal = function() {
  elements.imageModal.style.display = 'none';
};

// Toast notification helper
function showToast(msg, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerText = msg;
  elements.toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

// Copy link công khai
window.copyPublicLink = function() {
  const linkEl = document.getElementById('publicUrlLink');
  const url = linkEl ? linkEl.href : window.location.href;
  navigator.clipboard.writeText(url).then(() => {
    showToast('✓ Đã sao chép link công khai: ' + url, 'success');
  }).catch(() => {
    showToast('Link công khai: ' + url, 'info');
  });
};

// Tải thông tin mạng khi khởi động
async function loadNetworkInfo() {
  try {
    const res = await fetch('/api/network-info');
    if (res.ok) {
      const data = await res.json();
      const pubLink = document.getElementById('publicUrlLink');
      const lanCode = document.getElementById('lanUrlCode');
      if (pubLink && data.public_url) {
        pubLink.href = data.public_url;
        pubLink.innerText = data.public_url;
      }
      if (lanCode && data.lan_url) {
        lanCode.innerText = data.lan_url;
      }
    }
  } catch (e) {}
}

// Khởi chạy khi DOM sẵn sàng
document.addEventListener('DOMContentLoaded', () => {
  init();
  loadNetworkInfo();
});

