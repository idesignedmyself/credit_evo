/**
 * Credit Engine 2.0 - Profile Page
 * User profile management with identity and location info
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Alert,
  Grid,
  Divider,
  MenuItem,
  LinearProgress,
  InputAdornment,
  IconButton,
  Snackbar,
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  ArrowBack,
  Save,
  Person,
  Home,
  Lock,
} from '@mui/icons-material';
import { getProfile, updateProfile, changePassword } from '../api/authApi';

const US_STATES = [
  { code: 'AL', name: 'Alabama' }, { code: 'AK', name: 'Alaska' },
  { code: 'AZ', name: 'Arizona' }, { code: 'AR', name: 'Arkansas' },
  { code: 'CA', name: 'California' }, { code: 'CO', name: 'Colorado' },
  { code: 'CT', name: 'Connecticut' }, { code: 'DE', name: 'Delaware' },
  { code: 'FL', name: 'Florida' }, { code: 'GA', name: 'Georgia' },
  { code: 'HI', name: 'Hawaii' }, { code: 'ID', name: 'Idaho' },
  { code: 'IL', name: 'Illinois' }, { code: 'IN', name: 'Indiana' },
  { code: 'IA', name: 'Iowa' }, { code: 'KS', name: 'Kansas' },
  { code: 'KY', name: 'Kentucky' }, { code: 'LA', name: 'Louisiana' },
  { code: 'ME', name: 'Maine' }, { code: 'MD', name: 'Maryland' },
  { code: 'MA', name: 'Massachusetts' }, { code: 'MI', name: 'Michigan' },
  { code: 'MN', name: 'Minnesota' }, { code: 'MS', name: 'Mississippi' },
  { code: 'MO', name: 'Missouri' }, { code: 'MT', name: 'Montana' },
  { code: 'NE', name: 'Nebraska' }, { code: 'NV', name: 'Nevada' },
  { code: 'NH', name: 'New Hampshire' }, { code: 'NJ', name: 'New Jersey' },
  { code: 'NM', name: 'New Mexico' }, { code: 'NY', name: 'New York' },
  { code: 'NC', name: 'North Carolina' }, { code: 'ND', name: 'North Dakota' },
  { code: 'OH', name: 'Ohio' }, { code: 'OK', name: 'Oklahoma' },
  { code: 'OR', name: 'Oregon' }, { code: 'PA', name: 'Pennsylvania' },
  { code: 'RI', name: 'Rhode Island' }, { code: 'SC', name: 'South Carolina' },
  { code: 'SD', name: 'South Dakota' }, { code: 'TN', name: 'Tennessee' },
  { code: 'TX', name: 'Texas' }, { code: 'UT', name: 'Utah' },
  { code: 'VT', name: 'Vermont' }, { code: 'VA', name: 'Virginia' },
  { code: 'WA', name: 'Washington' }, { code: 'WV', name: 'West Virginia' },
  { code: 'WI', name: 'Wisconsin' }, { code: 'WY', name: 'Wyoming' },
  { code: 'DC', name: 'Washington D.C.' },
];

const SUFFIXES = ['Jr', 'Sr', 'II', 'III', 'IV', 'V'];

function ProfilePage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Profile fields
  const [profile, setProfile] = useState({
    email: '',
    username: '',
    first_name: '',
    middle_name: '',
    last_name: '',
    suffix: '',
    date_of_birth: '',
    ssn_last_4: '',
    phone: '',
    street_address: '',
    unit: '',
    city: '',
    state: '',
    zip_code: '',
    move_in_date: '',
    profile_complete: 0,
  });

  // Password fields
  const [passwords, setPasswords] = useState({
    current: '',
    new: '',
    confirm: '',
  });
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false,
  });
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordError, setPasswordError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState('');

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      setLoading(true);
      const data = await getProfile();
      setProfile({
        email: data.email || '',
        username: data.username || '',
        first_name: data.first_name || '',
        middle_name: data.middle_name || '',
        last_name: data.last_name || '',
        suffix: data.suffix || '',
        date_of_birth: data.date_of_birth || '',
        ssn_last_4: data.ssn_last_4 || '',
        phone: data.phone || '',
        street_address: data.street_address || '',
        unit: data.unit || '',
        city: data.city || '',
        state: data.state || '',
        zip_code: data.zip_code || '',
        move_in_date: data.move_in_date || '',
        profile_complete: data.profile_complete || 0,
      });
    } catch (err) {
      setError('Failed to load profile: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleProfileChange = (field) => (e) => {
    setProfile({ ...profile, [field]: e.target.value });
  };

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setSaving(true);

    try {
      const updateData = {
        first_name: profile.first_name || null,
        middle_name: profile.middle_name || null,
        last_name: profile.last_name || null,
        suffix: profile.suffix || null,
        date_of_birth: profile.date_of_birth || null,
        ssn_last_4: profile.ssn_last_4 || null,
        phone: profile.phone || null,
        street_address: profile.street_address || null,
        unit: profile.unit || null,
        city: profile.city || null,
        state: profile.state || null,
        zip_code: profile.zip_code || null,
        move_in_date: profile.move_in_date || null,
      };

      console.log('[ProfilePage] Saving profile with data:', updateData);
      const result = await updateProfile(updateData);
      console.log('[ProfilePage] Profile save response:', result);
      setProfile({
        ...profile,
        profile_complete: result.profile_complete,
      });
      setSuccess('Profile updated successfully!');
    } catch (err) {
      console.error('[ProfilePage] Profile save error:', err);
      setError(err.message || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordChange = (field) => (e) => {
    setPasswords({ ...passwords, [field]: e.target.value });
  };

  const togglePasswordVisibility = (field) => () => {
    setShowPasswords({ ...showPasswords, [field]: !showPasswords[field] });
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPasswordError('');
    setPasswordSuccess('');

    if (passwords.new !== passwords.confirm) {
      setPasswordError('New passwords do not match');
      return;
    }

    if (passwords.new.length < 8) {
      setPasswordError('New password must be at least 8 characters');
      return;
    }

    setPasswordSaving(true);
    try {
      await changePassword(passwords.current, passwords.new, passwords.confirm);
      setPasswordSuccess('Password changed successfully!');
      setPasswords({ current: '', new: '', confirm: '' });
    } catch (err) {
      setPasswordError(err.message || 'Failed to change password');
    } finally {
      setPasswordSaving(false);
    }
  };

  if (loading) {
    return (
      <Container maxWidth="md" sx={{ py: 4 }}>
        <LinearProgress />
        <Typography sx={{ mt: 2, textAlign: 'center' }}>Loading profile...</Typography>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Button
        startIcon={<ArrowBack />}
        onClick={() => navigate(-1)}
        sx={{ mb: 2 }}
      >
        Back
      </Button>

      <Typography variant="h4" gutterBottom>
        My Profile
      </Typography>

      {/* Profile Completeness */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="body1" sx={{ minWidth: 140 }}>
            Profile Completeness:
          </Typography>
          <Box sx={{ flexGrow: 1 }}>
            <LinearProgress
              variant="determinate"
              value={profile.profile_complete}
              sx={{ height: 10, borderRadius: 5 }}
            />
          </Box>
          <Typography variant="body1" fontWeight="bold">
            {profile.profile_complete}%
          </Typography>
        </Box>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          Complete your profile to enable accurate Statute of Limitations calculations and Mixed File detection.
        </Typography>
      </Paper>

      <Snackbar
        open={!!success}
        autoHideDuration={4000}
        onClose={() => setSuccess('')}
        message={success}
      />

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {/* Single form for both Identity and Address sections */}
      <Box component="form" onSubmit={handleSaveProfile}>
        {/* Identity Section */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <Person color="primary" />
            <Typography variant="h6">Identity Information</Typography>
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            This information helps detect Mixed File violations (accounts belonging to someone else with a similar name).
          </Typography>

          <Grid container spacing={2}>
            <Grid item xs={12} sm={4}>
              <TextField
                label="First Name"
                fullWidth
                value={profile.first_name}
                onChange={handleProfileChange('first_name')}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                label="Middle Name"
                fullWidth
                value={profile.middle_name}
                onChange={handleProfileChange('middle_name')}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                label="Last Name"
                fullWidth
                value={profile.last_name}
                onChange={handleProfileChange('last_name')}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                select
                label="Suffix"
                fullWidth
                value={profile.suffix}
                onChange={handleProfileChange('suffix')}
              >
                <MenuItem value="">None</MenuItem>
                {SUFFIXES.map((s) => (
                  <MenuItem key={s} value={s}>{s}</MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                label="Date of Birth"
                type="date"
                fullWidth
                value={profile.date_of_birth}
                onChange={handleProfileChange('date_of_birth')}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                label="SSN (Last 4)"
                fullWidth
                value={profile.ssn_last_4}
                onChange={handleProfileChange('ssn_last_4')}
                inputProps={{ maxLength: 4, pattern: '[0-9]{4}' }}
                helperText="For matching purposes only"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Phone"
                fullWidth
                value={profile.phone}
                onChange={handleProfileChange('phone')}
                placeholder="(555) 123-4567"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Email"
                fullWidth
                value={profile.email}
                disabled
                helperText="Email cannot be changed"
              />
            </Grid>
          </Grid>
        </Paper>

        {/* Address Section */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <Home color="primary" />
            <Typography variant="h6">Current Address</Typography>
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Your state of residence determines which Statute of Limitations applies to your debts.
          </Typography>

          <Grid container spacing={2}>
            <Grid item xs={12} sm={8}>
              <TextField
                label="Street Address"
                fullWidth
                value={profile.street_address}
                onChange={handleProfileChange('street_address')}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                label="Unit/Apt"
                fullWidth
                value={profile.unit}
                onChange={handleProfileChange('unit')}
              />
            </Grid>
            <Grid item xs={12} sm={5}>
              <TextField
                label="City"
                fullWidth
                value={profile.city}
                onChange={handleProfileChange('city')}
              />
            </Grid>
            <Grid item xs={12} sm={3}>
              <TextField
                select
                label="State"
                fullWidth
                value={profile.state}
                onChange={handleProfileChange('state')}
              >
                <MenuItem value="">Select...</MenuItem>
                {US_STATES.map((s) => (
                  <MenuItem key={s.code} value={s.code}>{s.code} - {s.name}</MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                label="ZIP Code"
                fullWidth
                value={profile.zip_code}
                onChange={handleProfileChange('zip_code')}
                placeholder="12345 or 12345-6789"
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                label="Move-in Date"
                type="date"
                fullWidth
                value={profile.move_in_date}
                onChange={handleProfileChange('move_in_date')}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
          </Grid>

          <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
            <Button
              type="submit"
              variant="contained"
              startIcon={<Save />}
              disabled={saving}
              size="large"
            >
              {saving ? 'Saving...' : 'Save Profile'}
            </Button>
          </Box>
        </Paper>
      </Box>

      {/* Password Section */}
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <Lock color="primary" />
          <Typography variant="h6">Change Password</Typography>
        </Box>

        {passwordError && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setPasswordError('')}>
            {passwordError}
          </Alert>
        )}
        {passwordSuccess && (
          <Alert severity="success" sx={{ mb: 2 }} onClose={() => setPasswordSuccess('')}>
            {passwordSuccess}
          </Alert>
        )}

        <Box component="form" onSubmit={handleChangePassword}>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField
                label="Current Password"
                type={showPasswords.current ? 'text' : 'password'}
                fullWidth
                value={passwords.current}
                onChange={handlePasswordChange('current')}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton onClick={togglePasswordVisibility('current')} edge="end">
                        {showPasswords.current ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="New Password"
                type={showPasswords.new ? 'text' : 'password'}
                fullWidth
                value={passwords.new}
                onChange={handlePasswordChange('new')}
                helperText="At least 8 characters"
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton onClick={togglePasswordVisibility('new')} edge="end">
                        {showPasswords.new ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Confirm New Password"
                type={showPasswords.confirm ? 'text' : 'password'}
                fullWidth
                value={passwords.confirm}
                onChange={handlePasswordChange('confirm')}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton onClick={togglePasswordVisibility('confirm')} edge="end">
                        {showPasswords.confirm ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>
          </Grid>

          <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
            <Button
              type="submit"
              variant="outlined"
              disabled={passwordSaving || !passwords.current || !passwords.new || !passwords.confirm}
            >
              {passwordSaving ? 'Changing...' : 'Change Password'}
            </Button>
          </Box>
        </Box>
      </Paper>
    </Container>
  );
}

export default ProfilePage;
