import { useState } from 'react'
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, Typography, Box, RadioGroup, FormControlLabel, Radio, FormControl, FormLabel } from '@mui/material'
import PropTypes from 'prop-types'
import PersonIcon from '@mui/icons-material/Person'
import SchoolIcon from '@mui/icons-material/School'

/**
 * Role Selection Dialog for Google Sign-In
 * Appears after Google authentication to let user choose their role
 */
export default function RoleSelectionDialog({ open, onClose, onSelectRole, userEmail }) {
  const [selectedRole, setSelectedRole] = useState('grihasta')

  const handleConfirm = () => {
    onSelectRole(selectedRole)
    onClose()
  }

  return (
    <Dialog 
      open={open} 
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 3,
          p: 2
        }
      }}
    >
      <DialogTitle sx={{ textAlign: 'center', pb: 1 }}>
        Complete Your Profile
      </DialogTitle>
      
      <DialogContent>
        <Typography variant="body2" color="text.secondary" align="center" sx={{ mb: 3 }}>
          Signing in as: <strong>{userEmail}</strong>
        </Typography>

        <FormControl component="fieldset" fullWidth>
          <FormLabel component="legend" sx={{ mb: 2, fontWeight: 600 }}>
            Select Your Role
          </FormLabel>
          <RadioGroup
            value={selectedRole}
            onChange={(e) => setSelectedRole(e.target.value)}
          >
            {/* Grihasta Option */}
            <Box
              sx={{
                border: '2px solid',
                borderColor: selectedRole === 'grihasta' ? 'primary.main' : 'divider',
                borderRadius: 2,
                p: 2,
                mb: 2,
                cursor: 'pointer',
                transition: 'all 0.2s',
                bgcolor: selectedRole === 'grihasta' ? 'primary.50' : 'transparent',
                '&:hover': {
                  borderColor: 'primary.main',
                  bgcolor: 'primary.50'
                }
              }}
              onClick={() => setSelectedRole('grihasta')}
            >
              <FormControlLabel
                value="grihasta"
                control={<Radio />}
                label={
                  <Box sx={{ ml: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <PersonIcon color="primary" />
                      <Typography variant="h6" fontWeight="600">
                        Grihasta (Seeker)
                      </Typography>
                    </Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                      Book services, connect with Acharyas, and explore spiritual traditions
                    </Typography>
                  </Box>
                }
                sx={{ m: 0, width: '100%' }}
              />
            </Box>

            {/* Acharya Option */}
            <Box
              sx={{
                border: '2px solid',
                borderColor: selectedRole === 'acharya' ? 'primary.main' : 'divider',
                borderRadius: 2,
                p: 2,
                cursor: 'pointer',
                transition: 'all 0.2s',
                bgcolor: selectedRole === 'acharya' ? 'primary.50' : 'transparent',
                '&:hover': {
                  borderColor: 'primary.main',
                  bgcolor: 'primary.50'
                }
              }}
              onClick={() => setSelectedRole('acharya')}
            >
              <FormControlLabel
                value="acharya"
                control={<Radio />}
                label={
                  <Box sx={{ ml: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <SchoolIcon color="primary" />
                      <Typography variant="h6" fontWeight="600">
                        Acharya (Service Provider)
                      </Typography>
                    </Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                      Offer services, share knowledge, and guide seekers
                    </Typography>
                  </Box>
                }
                sx={{ m: 0, width: '100%' }}
              />
            </Box>
          </RadioGroup>
        </FormControl>

        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 2, textAlign: 'center' }}>
          You can update your role later from account settings
        </Typography>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} color="inherit">
          Cancel
        </Button>
        <Button 
          onClick={handleConfirm} 
          variant="contained" 
          size="large"
          sx={{ minWidth: 120 }}
        >
          Continue
        </Button>
      </DialogActions>
    </Dialog>
  )
}

RoleSelectionDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onSelectRole: PropTypes.func.isRequired,
  userEmail: PropTypes.string
}
