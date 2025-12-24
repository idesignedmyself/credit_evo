/**
 * StatCard - Metric card component for admin dashboard
 */
import React from 'react';
import { Box, Card, CardContent, Typography, CircularProgress } from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';

export default function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  trendLabel,
  loading = false,
  color = '#e94560',
}) {
  const formatValue = (val) => {
    if (typeof val === 'number') {
      if (val >= 1000000) return `${(val / 1000000).toFixed(1)}M`;
      if (val >= 1000) return `${(val / 1000).toFixed(1)}K`;
      return val.toLocaleString();
    }
    return val;
  };

  return (
    <Card
      sx={{
        bgcolor: '#16213e',
        border: '1px solid #0f3460',
        borderRadius: 2,
        height: '100%',
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Typography variant="body2" sx={{ color: '#a2a2a2', fontWeight: 500 }}>
            {title}
          </Typography>
          {Icon && (
            <Box
              sx={{
                width: 40,
                height: 40,
                borderRadius: 1,
                bgcolor: `${color}20`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Icon sx={{ color, fontSize: 24 }} />
            </Box>
          )}
        </Box>

        {loading ? (
          <CircularProgress size={24} sx={{ color }} />
        ) : (
          <>
            <Typography variant="h4" sx={{ color: '#fff', fontWeight: 700, mb: 1 }}>
              {formatValue(value)}
            </Typography>

            {(subtitle || trend !== undefined) && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {trend !== undefined && (
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      color: trend >= 0 ? '#10b981' : '#ef4444',
                    }}
                  >
                    {trend >= 0 ? (
                      <TrendingUpIcon sx={{ fontSize: 16, mr: 0.5 }} />
                    ) : (
                      <TrendingDownIcon sx={{ fontSize: 16, mr: 0.5 }} />
                    )}
                    <Typography variant="caption" fontWeight={600}>
                      {Math.abs(trend)}%
                    </Typography>
                  </Box>
                )}
                {subtitle && (
                  <Typography variant="caption" sx={{ color: '#a2a2a2' }}>
                    {trendLabel || subtitle}
                  </Typography>
                )}
              </Box>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
