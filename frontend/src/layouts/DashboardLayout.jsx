/**
 * Credit Engine 2.0 - Dashboard Layout
 * Responsive sidebar layout with mobile hamburger menu
 */
import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import {
  AppBar, Box, CssBaseline, Drawer, IconButton, List, ListItem,
  ListItemButton, ListItemIcon, ListItemText, Toolbar, Typography,
  Avatar, Divider, Button
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import DashboardIcon from '@mui/icons-material/Dashboard';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import HistoryIcon from '@mui/icons-material/History';
import DescriptionIcon from '@mui/icons-material/Description';
import PersonIcon from '@mui/icons-material/Person';
import LogoutIcon from '@mui/icons-material/Logout';
import useAuthStore from '../state/authStore';
import useReportStore from '../state/reportStore';

const drawerWidth = 260;

const menuItems = [
  { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
  { text: 'Upload Report', icon: <UploadFileIcon />, path: '/upload' },
  { text: 'Report History', icon: <HistoryIcon />, path: '/reports' },
  { text: 'My Letters', icon: <DescriptionIcon />, path: '/letters' },
];

export default function DashboardLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const { latestReportId, fetchLatestReportId } = useReportStore();

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
    logout();
    navigate('/login');
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

  // Sidebar content
  const drawerContent = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Logo / Brand */}
      <Toolbar sx={{ px: 2 }}>
        <Typography variant="h6" noWrap sx={{ fontWeight: 'bold', color: 'primary.main' }}>
          Credit Engine
        </Typography>
      </Toolbar>
      <Divider />

      {/* Navigation Items */}
      <List sx={{ flexGrow: 1, px: 1 }}>
        {menuItems.map((item) => (
          <ListItem key={item.text} disablePadding sx={{ mb: 0.5 }}>
            <ListItemButton
              onClick={() => handleNavigation(item.path)}
              selected={isActive(item.path)}
              sx={{
                borderRadius: 2,
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
          sx={{ borderRadius: 2, mb: 1 }}
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
          sx={{ borderColor: 'divider', color: 'text.secondary' }}
        >
          Logout
        </Button>
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
              borderRight: '1px solid',
              borderColor: 'divider',
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
          width: { md: `calc(100% - ${drawerWidth}px)` },
          minHeight: '100vh',
          bgcolor: 'background.default',
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
