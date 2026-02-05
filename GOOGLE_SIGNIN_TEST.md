# Google Sign-In Testing Guide

## What Was Fixed

### Issues Found:
1. **Race condition**: Login page backdrop was closing before navigation completed
2. **Premature state clearing**: `setGoogleLoading(false)` was called too early
3. **Timing conflicts**: `setTimeout` delays were interfering with React Router navigation
4. **Mobile redirect flow**: Not handling role selection after OAuth redirect

### Solutions Applied:
1. **Keep backdrop open**: Loading state persists until route change unmounts the component
2. **Removed artificial delays**: No more `setTimeout` causing timing issues
3. **Added replace navigation**: Using `navigate(destination, { replace: true })` to prevent back button issues
4. **Better console logging**: Track the auth flow for debugging
5. **Mobile redirect support**: Detects pending auth and shows role dialog automatically

---

## Testing Steps

### Test 1: Google Sign-In with Grihasta Role (Desktop)
1. Stop all services: `.\stop-all.ps1`
2. Start fresh: `.\start-all.ps1`
3. Open browser: `http://localhost:3000/login`
4. Click **"Continue with Google"**
5. **Expected**: Google account selection popup appears
6. Select your Google account
7. **Expected**: Role selection dialog appears immediately
8. Select **"Grihasta"** role
9. **Expected**: 
   - Loading backdrop shows "Success! Redirecting to your dashboard..."
   - Automatically redirects to `/onboarding` (new user) or `/` (existing user)
   - Login page should NOT appear again
10. **Verify**: Check browser console for logs:
    ```
    Sending Google auth to backend with role: grihasta
    Google auth successful, user data: {...}
    Navigating to: /onboarding (or /)
    ```

### Test 2: Google Sign-In with Acharya Role (Desktop)
1. Log out if logged in
2. Go to `/login`
3. Click **"Continue with Google"**
4. Select Google account (different from Test 1 if possible)
5. Select **"Acharya"** role in dialog
6. **Expected**: Redirects to `/onboarding` or `/` based on onboarding status
7. **Verify**: User role is 'acharya' in profile/dashboard

### Test 3: Cancel Role Selection
1. Log out
2. Go to `/login`
3. Click **"Continue with Google"**
4. Select Google account
5. **Close the role dialog** without selecting
6. **Expected**: 
   - Toast message: "Google sign-in cancelled"
   - Stays on login page
   - Can try again

### Test 4: Mobile Redirect Flow (Mobile Device)
1. Open browser on mobile device
2. Navigate to login page
3. Click "Continue with Google"
4. **Expected**: Browser redirects to Google OAuth page (full page, not popup)
5. Authorize on Google
6. **Expected**: Redirects back to app with role dialog open
7. Select role
8. **Expected**: Completes authentication and navigates to dashboard

### Test 5: Existing User Login
1. Use Google account that already registered (has role in database)
2. Click "Continue with Google"
3. Select account
4. Select role (should match existing role)
5. **Expected**: 
   - If onboarded: Goes to `/` (Home)
   - If not onboarded: Goes to `/onboarding`
   - No loop back to login

---

## Console Debugging

### Look for these logs in browser console (F12):

**Successful Flow:**
```
Connecting to Google...
Sending Google auth to backend with role: grihasta
Google auth successful, user data: { email: "...", role: "grihasta", onboarded: false }
Navigating to: /onboarding
Welcome to Savitara!
```

**Error Handling:**
```
Google login failed: [error details]
Toast: "Google login failed. Please try again."
```

**Role Selection Cancel:**
```
Toast: "Google sign-in cancelled"
```

---

## Backend Verification

### Check Backend Logs:
1. Open the backend terminal window
2. After Google sign-in, look for:
   ```
   POST /auth/google - Status 200 OK
   User created/logged in: [email]
   ```

### Database Check:
```powershell
# In backend directory
python verify_db.py
```
- Verify new users have correct role field
- Verify tokens are saved correctly

---

## Common Issues & Solutions

### Issue: Still redirecting to login
**Solution**: Clear browser cache and localStorage
```javascript
// Run in browser console
localStorage.clear()
location.reload()
```

### Issue: "No pending authentication"
**Solution**: This means the token was lost. Try the flow again from start.

### Issue: Backend 401/403 error
**Solution**: 
1. Check backend logs for detailed error
2. Verify Firebase token is valid
3. Check backend `/auth/google` endpoint accepts both `id_token` and `role`

### Issue: Navigation doesn't happen
**Solution**: 
1. Check browser console for navigation logs
2. Verify user state is set: `console.log(localStorage.getItem('accessToken'))`
3. Check App.jsx routing guards

---

## Success Criteria

✅ **All tests must pass:**
1. Google Sign-In completes without returning to login page
2. Role selection works for both grihasta and acharya
3. New users go to onboarding
4. Existing users go to home/dashboard
5. Cancellation works without breaking the flow
6. Mobile redirect flow handles role selection
7. No console errors during the flow

---

## Next Steps After Testing

If all tests pass:
- Document the working flow
- Update main README with Google Sign-In instructions
- Consider adding rate limiting for auth endpoints
- Add analytics to track auth success/failure rates

If tests fail:
- Check browser console for errors
- Check backend logs for API errors
- Verify Firebase configuration
- Review network tab (F12 → Network) for failed requests
