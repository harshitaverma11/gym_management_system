(function() {
  var override = window.GYM_API_BASE_URL || localStorage.getItem('gymApiBaseUrl');
  var isLocalHost = ['localhost', '127.0.0.1', '::1', '[::1]', '0.0.0.0', '[::]'].indexOf(window.location.hostname) !== -1;
  var isLocalFile = window.location.protocol === 'file:';
  var baseUrl = override || (isLocalHost || isLocalFile ? 'http://127.0.0.1:5000' : window.location.origin);

  window.GYM_API_BASE_URL = String(baseUrl || '').replace(/\/$/, '');
})();