import { initializeApp } from 'firebase/app'
import { getMessaging, getToken, onMessage } from 'firebase/messaging'
import { 
  getAuth, 
  GoogleAuthProvider, 
  signInWithPopup,
  signInWithRedirect,
  getRedirectResult,
  signOut,
  onAuthStateChanged 
} from 'firebase/auth'

// Firebase configuration with provided credentials
const firebaseConfig = {
  apiKey: "AIzaSyABhtSIIz-mjMqArISDtnUAsPsv9eYD2c8",
  authDomain: "savitara-90a1c.firebaseapp.com",
  projectId: "savitara-90a1c",
  storageBucket: "savitara-90a1c.firebasestorage.app",
  messagingSenderId: "397566787449",
  appId: "1:397566787449:web:eb5fca6f1b7a0272dc79a8"
}

// Initialize Firebase
const app = initializeApp(firebaseConfig)

// Initialize Firebase Auth
export const auth = getAuth(app)
export const googleProvider = new GoogleAuthProvider()

// Add scopes for additional user info
googleProvider.addScope('email')
googleProvider.addScope('profile')

// Helper function to detect mobile devices
const isMobileDevice = () => {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
}

// Check for redirect result on page load (for mobile redirect flow)
export const checkRedirectResult = async () => {
  try {
    console.log('🔍 Checking for redirect result...')
    const result = await getRedirectResult(auth)
    if (result) {
      console.log('✅ Got redirect result, user:', result.user.email)
      const idToken = await result.user.getIdToken()
      return {
        user: {
          uid: result.user.uid,
          email: result.user.email,
          displayName: result.user.displayName,
          photoURL: result.user.photoURL,
        },
        idToken
      }
    }
    console.log('📭 No redirect result found')
    return null
  } catch (error) {
    console.error('❌ Redirect result error:', error)
    // Don't throw - just return null if no redirect result
    return null
  }
}

// Sign in with Google using popup (with redirect fallback for mobile)
export const signInWithGoogle = async () => {
  try {
    console.log('🔄 Starting Google Sign-In...')
    
    // Use popup on desktop, redirect on mobile
    if (isMobileDevice()) {
      console.log('📱 Mobile detected - using redirect flow')
      await signInWithRedirect(auth, googleProvider)
      // This line won't be reached - page will redirect to Google
      return null
    } else {
      console.log('💻 Desktop detected - using popup flow')
      const result = await signInWithPopup(auth, googleProvider)
      console.log('✅ Google Sign-In successful, user:', result.user.email)
      
      // Get ID token (force refresh to ensure it's valid)
      const idToken = await result.user.getIdToken(true)
      console.log('🔑 ID Token obtained (first 50 chars):', idToken.substring(0, 50) + '...')
      console.log('🔑 Token length:', idToken.length)
      
      return {
        user: {
          uid: result.user.uid,
          email: result.user.email,
          displayName: result.user.displayName,
          photoURL: result.user.photoURL,
        },
        idToken
      }
    }
  } catch (error) {
    console.error('❌ Google sign-in error:', error)
    console.error('Error code:', error.code)
    console.error('Error message:', error.message)
    
    // Provide user-friendly error messages
    let errorMessage
    
    switch (error.code) {
      case 'auth/popup-closed-by-user':
        errorMessage = 'Sign-in cancelled. Please try again.'
        break
      case 'auth/popup-blocked':
        errorMessage = 'Popup blocked by browser. Please allow popups and try again.'
        break
      case 'auth/operation-not-allowed':
        errorMessage = 'Google Sign-In is not enabled. Please contact support.'
        break
      case 'auth/unauthorized-domain':
        errorMessage = 'This domain is not authorized for Google Sign-In.'
        break
      case 'auth/network-request-failed':
        errorMessage = 'Network error. Please check your internet connection.'
        break
      case 'auth/cancelled-popup-request':
        errorMessage = 'Only one popup request is allowed at a time.'
        break
      default:
        errorMessage = error.message || 'Google sign-in failed. Please try again.'
    }
    
    const enhancedError = new Error(errorMessage)
    enhancedError.code = error.code
    enhancedError.originalError = error
    throw enhancedError
  }
}

// Sign out from Firebase
export const firebaseSignOut = async () => {
  try {
    await signOut(auth)
  } catch (error) {
    console.error('Sign out error:', error)
    throw error
  }
}

// Listen to auth state changes
export const onAuthChange = (callback) => {
  return onAuthStateChanged(auth, callback)
}

// Initialize Firebase Cloud Messaging
let messaging = null
try {
  messaging = getMessaging(app)
} catch (error) {
  console.error('Firebase messaging initialization failed:', error)
}

// Request notification permission and get FCM token
export const requestNotificationPermission = async () => {
  if (!messaging) {
    console.warn('Firebase messaging not available')
    return null
  }

  try {
    const permission = await Notification.requestPermission()
    if (permission === 'granted') {
      const token = await getToken(messaging, {
        vapidKey: import.meta.env.VITE_FIREBASE_VAPID_KEY,
      })
      return token
    } else {
      console.log('Notification permission denied')
      return null
    }
  } catch (error) {
    console.error('Error getting notification permission:', error)
    return null
  }
}

// Listen for foreground messages
export const onMessageListener = (callback) => {
  if (!messaging) {
    console.warn('Firebase messaging not available')
    return () => {}
  }

  return onMessage(messaging, (payload) => {
    console.log('Message received in foreground:', payload)
    callback(payload)
  })
}

export default app
