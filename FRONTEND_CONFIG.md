## Frontend Configuration for Render Deployment

After deploying your backend to Render, update the frontend to use the correct API endpoint.

### Option 1: Update in HTML Files (Recommended for Static Sites)

Find all instances of `http://localhost:5000` in your HTML files and replace with your Render backend URL:

```bash
# Search for all API calls
grep -r "localhost:5000" frontend/
```

Replace with: `https://gym-backend.onrender.com` (or your actual Render domain)

### Option 2: Create a Configuration File

Create `frontend/js/config.js`:
```javascript
const API_URL = window.location.hostname === 'localhost' 
  ? 'http://localhost:5000'
  : 'https://gym-backend.onrender.com';

// Use in fetch calls:
// fetch(`${API_URL}/login`, {...})
```

Then include in your HTML:
```html
<script src="js/config.js"></script>
```

### Common Frontend Files to Update

Search for and update these files:
- `js/*.js` - API endpoints
- `*.html` - Any hardcoded localhost URLs
- `css/*.css` - Any backend-served static assets

### Testing After Deployment

1. Open https://gym-frontend.onrender.com
2. Right-click → Inspect → Network tab
3. Try logging in and watch API requests
4. Verify requests go to `https://gym-backend.onrender.com/` (not localhost)

### If You See CORS Errors

Check that your Render backend has the correct `ALLOWED_ORIGINS` environment variable set to include your frontend domain.
