import { createContext, useState, useContext, useEffect, useMemo } from 'react'
import PropTypes from 'prop-types'
import { useNavigate } from 'react-router-dom'
import api from '../services/api.js'
import { signInWithGoogle as firebaseGoogleSignIn, checkRedirectResult, firebaseSignOut } from '../services/firebase'
import { toast } from 'react-toastify'

const AuthContext = createContext({})

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [pendingGoogleAuth, setPendingGoogleAuth] = useState(null) // Store Google token until role is selected
  const navigate = useNavigate()

  useEffect(() => {
    const initAuth = async () => {
      // First check for redirect result (for mobile flow)
      try {
        const redirectResult = await checkRedirectResult()
        if (redirectResult?.idToken) {
          console.log('Processing redirect result from mobile OAuth...')
          // For redirect flow, we also need role selection
          setPendingGoogleAuth({ 
            idToken: redirectResult.idToken, 
            userEmail: redirectResult.user?.email 
          })
          // Don't auto-login - let user select role first
          setLoading(false)
          return
        }
      } catch (error) {
        console.warn('No redirect result:', error)
      }
      
      // Then check regular auth
      checkAuth()
    }
    
    initAuth()
  }, [])

  const checkAuth = async () => {
    const accessToken = localStorage.getItem('accessToken')
    const refreshToken = localStorage.getItem('refreshToken')

    if (!accessToken || !refreshToken) {
      setLoading(false)
      return
    }

    try {
      const response = await api.get('/auth/me')
      // Extract user data from StandardResponse format
      const userData = response.data.data || response.data
      setUser(userData)
    } catch (error) {
      console.error('Auth check failed:', error)
      localStorage.removeItem('accessToken')
      localStorage.removeItem('refreshToken')
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  const loginWithEmail = async (email, password) => {
    try {
      const response = await api.post('/auth/login', { email, password })
      // Backend returns StandardResponse: { success, data: {...}, message }
      const { access_token, refresh_token, user: userData } = response.data.data || response.data

      localStorage.setItem('accessToken', access_token)
      localStorage.setItem('refreshToken', refresh_token)
      
      setUser(userData)
      
      // Navigate based on onboarding status - Home after login
      if (userData.onboarded || userData.onboarding_completed) {
        navigate('/')
      } else {
        navigate('/onboarding')
      }

      toast.success('Login successful!')
    } catch (error) {
      console.error('Login failed:', error)
      // Show specific error message from backend
      const errorMessage = error.response?.data?.detail || 'Login failed'
      toast.error(errorMessage)
      throw error
    }
  }

  const registerWithEmail = async (data) => {
    try {
      setLoading(true)
      console.log('Sending registration request with data:', { ...data, password: '[REDACTED]' })
      const response = await api.post('/auth/register', data)
      console.log('Registration response:', response)
      
      // Backend returns StandardResponse: { success, data: {...}, message }
      const { access_token, refresh_token, user: userData } = response.data.data || response.data

      localStorage.setItem('accessToken', access_token)
      localStorage.setItem('refreshToken', refresh_token)
      
      setUser(userData)
      // New users always go to onboarding
      navigate('/onboarding')
      toast.success('Registration successful! Please complete your profile.')
    } catch (error) {
      console.error('Registration failed:', error)
      console.error('Error details:', {
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
        headers: error.response?.headers
      })
      const errorMessage = error.response?.data?.detail 
        || error.response?.data?.message 
        || error.message 
        || 'Registration failed. Please try again.'
      toast.error(errorMessage)
      throw error
    } finally {
      setLoading(false)
    }
  }

  // Updated to use Firebase Google Sign-In with popup
  const loginWithGoogle = async (legacyCredential = null) => {
    try {
      let idToken
      let userEmail = null

      // If called with a credential (legacy @react-oauth/google), use it
      if (legacyCredential) {
        idToken = legacyCredential
      } else {
        // Use Firebase Google Sign-In (popup or redirect based on device)
        const result = await firebaseGoogleSignIn()
        
        // If null, redirect happened (mobile) - user will come back via redirect
        if (!result) {
          console.log('Redirect initiated - user will return after authentication')
          return
        }
        
        idToken = result.idToken
        userEmail = result.user?.email
      }

      // Store the token and user info for role selection
      setPendingGoogleAuth({ idToken, userEmail })
      
      // Return true to indicate we need role selection
      return { needsRoleSelection: true, userEmail }
      
    } catch (error) {
      console.error('Login failed:', error)
      toast.error(error.message || 'Login failed')
      throw error
    }
  }
  
  // Complete Google login after role selection
  const completeGoogleLogin = async (role) => {
    if (!pendingGoogleAuth) {
      toast.error('No pending authentication. Please try again.')
      return
    }
    
    try {
      await handleGoogleLogin(pendingGoogleAuth.idToken, role)
      setPendingGoogleAuth(null) // Clear pending auth
    } catch (error) {
      console.error('Failed to complete Google login:', error)
      toast.error(error.message || 'Failed to complete login')
      throw error
    }
  }
  
  // Cancel Google login
  const cancelGoogleLogin = () => {
    setPendingGoogleAuth(null)
  }
  
  // Helper function to process Google login with backend (updated to accept role)
  const handleGoogleLogin = async (idToken, role) => {
    try {
      console.log('Sending Google auth to backend with role:', role)
      
      // Send token to backend with correct field name and role
      const response = await api.post('/auth/google', {
        id_token: idToken,  // Backend expects 'id_token', not 'token'
        role: role          // User-selected role (grihasta or acharya)
      })

      const { data } = response.data // Backend returns StandardResponse with data field
      const { access_token, refresh_token, user: userData } = data
      
      console.log('Google auth successful, user data:', { 
        email: userData.email, 
        role: userData.role, 
        onboarded: userData.onboarded || userData.onboarding_completed 
      })
      
      localStorage.setItem('accessToken', access_token)
      localStorage.setItem('refreshToken', refresh_token)
      
      setUser(userData)
      
      toast.success('Welcome to Savitara!')
      
      // Check if user needs onboarding - Navigate after state update
      const isOnboarded = userData.onboarded || userData.onboarding_completed
      const destination = isOnboarded ? '/' : '/onboarding'
      
      console.log('Navigating to:', destination)
      navigate(destination, { replace: true })
      
    } catch (error) {
      console.error('Backend login failed:', error)
      const errorMsg = error.response?.data?.detail || error.response?.data?.message || 'Authentication failed'
      toast.error(errorMsg)
      throw error
    }
  }

  const logout = async () => {
    try {
      await api.post('/auth/logout')
    } catch (error) {
      console.error('Logout API failed:', error)
    }
    
    // Also sign out from Firebase
    try {
      await firebaseSignOut()
    } catch (error) {
      console.error('Firebase sign out failed:', error)
    }
    
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
    setUser(null)
    navigate('/login')
    toast.info('Logged out successfully')
  }

  const updateUser = (userData) => {
    setUser(userData)
  }

  const refreshUserData = async () => {
    try {
      const response = await api.get('/auth/me')
      // Handle StandardResponse format from backend
      const userData = response.data.data || response.data
      setUser(userData)
    } catch (error) {
      console.error('Failed to refresh user data:', error)
    }
  }

  const value = useMemo(() => ({
    user,
    loading,
    loginWithGoogle,
    completeGoogleLogin,
    cancelGoogleLogin,
    pendingGoogleAuth,
    loginWithEmail,
    registerWithEmail,
    logout,
    updateUser,
    refreshUserData,
  }), [user, loading, pendingGoogleAuth])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

AuthProvider.propTypes = {
  children: PropTypes.node.isRequired,
}
