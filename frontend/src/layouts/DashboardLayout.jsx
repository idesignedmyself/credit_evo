/**
 * Credit Engine 2.0 - Dashboard Layout
 * Responsive sidebar layout with mobile hamburger menu
 * Includes persistent Copilot drawer (right side)
 */
import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import {
  AppBar, Box, CssBaseline, Drawer, IconButton, List, ListItem,
  ListItemButton, ListItemIcon, ListItemText, Toolbar, Typography,
  Avatar, Divider, Button, Fab, Tooltip, useTheme, useMediaQuery
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import DashboardIcon from '@mui/icons-material/Dashboard';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import HistoryIcon from '@mui/icons-material/History';
import DescriptionIcon from '@mui/icons-material/Description';
import GavelIcon from '@mui/icons-material/Gavel';
import PersonIcon from '@mui/icons-material/Person';
import LogoutIcon from '@mui/icons-material/Logout';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import useAuthStore from '../state/authStore';
import useReportStore from '../state/reportStore';
import useViolationStore from '../state/violationStore';
import useUIStore from '../state/uiStore';
import useCopilotStore from '../state/copilotStore';
import { CopilotDrawer, FeatureGate } from '../components/copilot';

const drawerWidth = 260;
const copilotDrawerWidth = 380;

const menuItems = [
  { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
  { text: 'Upload Report', icon: <UploadFileIcon />, path: '/upload' },
  { text: 'Report History', icon: <HistoryIcon />, path: '/reports' },
  { text: 'My Letters', icon: <DescriptionIcon />, path: '/letters' },
  { text: 'Dispute Tracking', icon: <GavelIcon />, path: '/disputes' },
];

export default function DashboardLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { user, logout } = useAuthStore();
  const { latestReportId, fetchLatestReportId, resetState: resetReportState } = useReportStore();
  const { resetState: resetViolationState } = useViolationStore();
  const { resetState: resetUIState } = useUIStore();
  const { drawerOpen: copilotDrawerOpen, toggleDrawer: toggleCopilotDrawer, resetState: resetCopilotState } = useCopilotStore();

  // Fetch latest report ID on mount (for Dashboard navigation)
  useEffect(() => {
    fetchLatestReportId();
  }, [fetchLatestReportId]);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleNavigation = (path) => {
    // For Dashboard, navigate directly to audit page if we have a report
    if (path === '/dashboard' && latestReportId) {
      navigate(`/audit/${latestReportId}`);
    } else {
      navigate(path);
    }
    setMobileOpen(false);
  };

  const handleLogout = () => {
    // Reset all stores on logout to clear user data
    resetViolationState();
    resetUIState();
    resetReportState();
    resetCopilotState();
    logout();
    // Scroll to top before navigating so landing page shows from the top
    window.scrollTo(0, 0);
    navigate('/');
  };

  const isActive = (path) => {
    if (path === '/dashboard') {
      // Dashboard is active when on /dashboard, /, or any /audit/* page
      return location.pathname === '/dashboard' ||
             location.pathname === '/' ||
             location.pathname.startsWith('/audit');
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
    return 'U';
  };

  // Sidebar content - floating card on background
  const drawerContent = (
    <Box sx={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      bgcolor: 'background.default',
      p: 1.5,
    }}>
      {/* Floating Card Container */}
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          flexGrow: 1,
          bgcolor: 'background.paper',
          borderRadius: '12px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
          border: '1px solid #E2E8F0',
          overflow: 'hidden',
        }}
      >
        {/* Logo / Brand */}
        <Toolbar sx={{ px: 2 }}>
          <Typography variant="h6" noWrap sx={{ fontWeight: 'bold', color: 'primary.main' }}>
            Credit Engine
          </Typography>
        </Toolbar>
        <Divider />

        {/* Navigation Items */}
        <List sx={{ flexGrow: 1, px: 1, py: 1 }}>
          {menuItems.map((item) => (
            <ListItem key={item.text} disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton
                onClick={() => handleNavigation(item.path)}
                selected={isActive(item.path)}
                sx={{
                  borderRadius: '8px',
                  '&.Mui-selected': {
                    bgcolor: 'primary.main',
                    color: 'white',
                    '&:hover': { bgcolor: 'primary.dark' },
                    '& .MuiListItemIcon-root': { color: 'white' },
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: 40 }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText primary={item.text} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>

        <Divider />

        {/* User Section */}
        <Box sx={{ p: 2 }}>
          <ListItemButton
            onClick={() => handleNavigation('/profile')}
            selected={isActive('/profile')}
            sx={{ borderRadius: '8px', mb: 1 }}
          >
            <Avatar sx={{ width: 32, height: 32, mr: 2, bgcolor: 'primary.main', fontSize: '0.875rem' }}>
              {getInitials()}
            </Avatar>
            <ListItemText
              primary={user?.first_name ? `${user.first_name} ${user.last_name || ''}`.trim() : user?.username || user?.email}
              primaryTypographyProps={{ variant: 'body2', fontWeight: 500, noWrap: true }}
              secondary="View Profile"
              secondaryTypographyProps={{ variant: 'caption' }}
            />
          </ListItemButton>
          <Button
            fullWidth
            variant="outlined"
            color="inherit"
            startIcon={<LogoutIcon />}
            onClick={handleLogout}
            size="small"
            sx={{ borderColor: 'divider', color: 'text.secondary', borderRadius: '8px' }}
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
          bgcolor: 'background.paper',
          borderBottom: '1px solid',
          borderColor: 'divider',
          display: { md: 'none' },
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, color: 'text.primary' }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap sx={{ color: 'primary.main', fontWeight: 'bold' }}>
            Credit Engine
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
              bgcolor: 'background.default',
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
          bgcolor: 'background.default',
          // MUI Drawer uses position:fixed, so we need margin to push content
          marginRight: copilotDrawerOpen && !isMobile ? `${copilotDrawerWidth}px` : 0,
          transition: theme.transitions.create('margin-right', {
            duration: theme.transitions.duration.enteringScreen,
            easing: theme.transitions.easing.easeOut,
          }),
        }}
      >
        {/* Spacer for mobile AppBar */}
        <Toolbar sx={{ display: { md: 'none' } }} />

        {/* Page Content */}
        <Outlet />
      </Box>

      {/* Copilot FAB - Toggle drawer */}
      <FeatureGate feature="copilot">
        <Tooltip title={copilotDrawerOpen ? 'Close Copilot' : 'Open Credit Copilot'}>
          <Fab
            color="primary"
            size="medium"
            onClick={toggleCopilotDrawer}
            sx={{
              position: 'fixed',
              bottom: 24,
              // Position FAB to the left of the drawer when open
              right: copilotDrawerOpen && !isMobile ? copilotDrawerWidth + 24 : 24,
              transition: theme.transitions.create('right', {
                duration: theme.transitions.duration.enteringScreen,
                easing: theme.transitions.easing.easeOut,
              }),
              zIndex: theme.zIndex.drawer + 1,
            }}
          >
            <SmartToyIcon />
          </Fab>
        </Tooltip>
      </FeatureGate>

      {/* Copilot Drawer */}
      <FeatureGate feature="copilot">
        <CopilotDrawer />
      </FeatureGate>
    </Box>
  );
}
