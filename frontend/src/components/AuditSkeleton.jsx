/**
 * Audit Page Skeleton Loader
 * Mimics the AuditPage layout with animated placeholders for faster perceived loading
 */
import React from 'react';
import { Box, Grid, Skeleton, Stack, Paper, Container } from '@mui/material';

export default function AuditSkeleton() {
  return (
    <Box>
      {/* 1. Score Dashboard Section */}
      {/* Score Cards Row (mimics the 3 Bureau Scores) */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {[1, 2, 3].map((item) => (
          <Grid item xs={12} md={4} key={item}>
            <Skeleton
              variant="rectangular"
              height={140}
              sx={{ borderRadius: 4, bgcolor: 'rgba(0,0,0,0.08)' }}
            />
          </Grid>
        ))}
      </Grid>

      {/* Stats Row (mimics the 4 stat chips) */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {[1, 2, 3, 4].map((item) => (
          <Grid item xs={6} md={3} key={item}>
            <Skeleton
              variant="rectangular"
              height={80}
              sx={{ borderRadius: 3, bgcolor: 'rgba(0,0,0,0.06)' }}
            />
          </Grid>
        ))}
      </Grid>

      {/* 2. Action Bar Mimic */}
      <Skeleton
        variant="rectangular"
        height={70}
        sx={{ mb: 4, borderRadius: 2, bgcolor: 'rgba(33, 150, 243, 0.1)' }}
      />

      {/* 3. Filter Toolbar Mimic */}
      <Skeleton variant="rectangular" height={60} sx={{ mb: 3, borderRadius: 2 }} />

      {/* 4. Violation List (mimics Accordions) */}
      <Stack spacing={2}>
        {[1, 2, 3, 4, 5].map((item) => (
          <Paper
            key={item}
            elevation={0}
            sx={{ p: 3, border: '1px solid #eee', borderRadius: 3 }}
          >
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Box>
                {/* Title Line */}
                <Skeleton variant="text" width={250} height={30} sx={{ mb: 1 }} />
                {/* Subtitle Line */}
                <Skeleton variant="text" width={180} height={20} />
              </Box>
              {/* The Severity Chip */}
              <Skeleton variant="rounded" width={60} height={24} sx={{ borderRadius: 4 }} />
            </Stack>
          </Paper>
        ))}
      </Stack>
    </Box>
  );
}
