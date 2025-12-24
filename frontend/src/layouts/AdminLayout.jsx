/**
 * Credit Engine 2.0 - Admin Layout
 * Read-only intelligence console built on Execution Ledger truth.
 * Admin observes, correlates, diagnoses - never mutates.
 */
import React, { useState } from 'react';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import {
  AppBar, Box, CssBaseline, Drawer, IconButton, List, ListItem,
  ListItemButton, ListItemIcon, ListItemText, Toolbar, Typography,
  Avatar, Divider, Button, Chip, useTheme, useMediaQuery
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import DashboardIcon from '@mui/icons-material/Dashboard';
import PeopleIcon from '@mui/icons-material/People';
import InsightsIcon from '@mui/icons-material/Insights';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import LogoutIcon from '@mui/icons-material/Logout';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings';
import useAuthStore from '../state/authStore';

const drawerWidth = 260;

const adminMenuItems = [
  { text: 'Dashboard', icon: <DashboardIcon />, path: '/admin' },
  { text: 'Users', icon: <PeopleIcon />, path: '/admin/users' },
  { text: 'Dispute Intelligence', icon: <InsightsIcon />, path: '/admin/disputes' },
  { text: 'Copilot Performance', icon: <SmartToyIcon />, path: '/admin/copilot' },
];

export default function AdminLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { user, logout } = useAuthStore();

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleNavigation = (path) => {
    navigate(path);
    setMobileOpen(false);
  };

  const handleLogout = () => {
    logout();
    window.scrollTo(0, 0);
    navigate('/');
  };

  const handleBackToApp = () => {
    navigate('/dashboard');
  };

  const isActive = (path) => {
    if (path === '/admin') {
      return location.pathname === '/admin';
    }
    return location.pathname.startsWith(path);
  };

  // Get user initials for avatar
  const getInitials = () => {
    if (user?.first_name && user?.last_name) {
      return `${user.first_name[0]}${user.last_name[0]}`.toUpperCase();
    }
    if (user?.username) {
      return user.username.slice(0, 2).toUpperCase();
    }
    if (user?.email) {
      return user.email.slice(0, 2).toUpperCase();
    }
    return 'A';
  };

  // Sidebar content - floating card on dark background
  const drawerContent = (
    <Box sx={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      bgcolor: '#1a1a2e',
      p: 1.5,
    }}>
      {/* Floating Card Container */}
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          flexGrow: 1,
          bgcolor: '#16213e',
          borderRadius: '12px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          border: '1px solid #0f3460',
          overflow: 'hidden',
        }}
      >
        {/* Logo / Brand */}
        <Toolbar sx={{ px: 2 }}>
          <AdminPanelSettingsIcon sx={{ mr: 1, color: '#e94560' }} />
          <Typography variant="h6" noWrap sx={{ fontWeight: 'bold', color: '#e94560' }}>
            Admin Console
          </Typography>
        </Toolbar>
        <Divider sx={{ borderColor: '#0f3460' }} />

        {/* Back to App Button */}
        <Box sx={{ px: 2, py: 1 }}>
          <Button
            fullWidth
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={handleBackToApp}
            size="small"
            sx={{
              borderColor: '#0f3460',
              color: '#a2a2a2',
              borderRadius: '8px',
              '&:hover': {
                borderColor: '#e94560',
                color: '#e94560',
              }
            }}
          >
            Back to App
          </Button>
        </Box>

        <Divider sx={{ borderColor: '#0f3460' }} />

        {/* Navigation Items */}
        <List sx={{ flexGrow: 1, px: 1, py: 1 }}>
          {adminMenuItems.map((item) => (
            <ListItem key={item.text} disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton
                onClick={() => handleNavigation(item.path)}
                selected={isActive(item.path)}
                sx={{
                  borderRadius: '8px',
                  color: '#a2a2a2',
                  '&:hover': {
                    bgcolor: 'rgba(233, 69, 96, 0.1)',
                    color: '#fff',
                  },
                  '&.Mui-selected': {
                    bgcolor: '#e94560',
                    color: 'white',
                    '&:hover': { bgcolor: '#d63353' },
                    '& .MuiListItemIcon-root': { color: 'white' },
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: 40, color: 'inherit' }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText primary={item.text} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>

        <Divider sx={{ borderColor: '#0f3460' }} />

        {/* User Section */}
        <Box sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Avatar sx={{ width: 32, height: 32, mr: 2, bgcolor: '#e94560', fontSize: '0.875rem' }}>
              {getInitials()}
            </Avatar>
            <Box sx={{ flexGrow: 1, minWidth: 0 }}>
              <Typography variant="body2" fontWeight={500} noWrap sx={{ color: '#fff' }}>
                {user?.first_name ? `${user.first_name} ${user.last_name || ''}`.trim() : user?.username || user?.email}
              </Typography>
              <Chip
                label="Admin"
                size="small"
                sx={{
                  height: 18,
                  fontSize: '0.65rem',
                  bgcolor: '#e94560',
                  color: '#fff'
                }}
              />
            </Box>
          </Box>
          <Button
            fullWidth
            variant="outlined"
            startIcon={<LogoutIcon />}
            onClick={handleLogout}
            size="small"
            sx={{
              borderColor: '#0f3460',
              color: '#a2a2a2',
              borderRadius: '8px',
              '&:hover': {
                borderColor: '#e94560',
                color: '#e94560',
              }
            }}
          >
            Logout
          </Button>
        </Box>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />

      {/* App Bar - Mobile Only */}
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          width: { md: `calc(100% - ${drawerWidth}px)` },
          ml: { md: `${drawerWidth}px` },
          bgcolor: '#1a1a2e',
          borderBottom: '1px solid #0f3460',
          display: { md: 'none' },
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, color: '#e94560' }}
          >
            <MenuIcon />
          </IconButton>
          <AdminPanelSettingsIcon sx={{ mr: 1, color: '#e94560' }} />
          <Typography variant="h6" noWrap sx={{ color: '#e94560', fontWeight: 'bold' }}>
            Admin Console
          </Typography>
        </Toolbar>
      </AppBar>

      {/* Sidebar Navigation */}
      <Box
        component="nav"
        sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}
      >
        {/* Mobile Drawer (Temporary) */}
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', md: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
        >
          {drawerContent}
        </Drawer>

        {/* Desktop Drawer (Permanent) */}
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', md: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
              border: 'none',
              bgcolor: '#1a1a2e',
            },
          }}
          open
        >
          {drawerContent}
        </Drawer>
      </Box>

      {/* Main Content Area */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          minHeight: '100vh',
          bgcolor: '#0f0f1a',
        }}
      >
        {/* Spacer for mobile AppBar */}
        <Toolbar sx={{ display: { md: 'none' } }} />

        {/* Page Content */}
        <Outlet />
      </Box>
    </Box>
  );
}
