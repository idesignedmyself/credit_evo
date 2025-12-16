/**
 * Credit Engine 2.0 - Score Dashboard Component
 * Displays bureau scores
 */
import React from 'react';
import { Box, Grid, Card, CardContent, Typography, LinearProgress, Chip } from '@mui/material';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import { BUREAU_COLORS } from '../theme';

// Calculate score percentile (where score falls in 300-850 range)
function getScorePercentile(score) {
  if (!score || score === 0) return 0;
  const min = 300;
  const max = 850;
  const percentile = Math.round(((score - min) / (max - min)) * 100);
  return Math.max(0, Math.min(100, percentile));
}

// Get progress bar value (normalized to 0-100)
function getProgressValue(score) {
  if (!score || score === 0) return 0;
  const min = 300;
  const max = 850;
  return Math.round(((score - min) / (max - min)) * 100);
}

// Get lender tier based on score
function getLenderTier(score) {
  if (!score || score === 0) return { tier: null, name: 'No Score' };
  if (score >= 720) return { tier: 1, name: 'Prime / Super Prime' };
  if (score >= 680) return { tier: 2, name: 'Prime / Near-Prime' };
  if (score >= 630) return { tier: 3, name: 'Subprime Tier 3' };
  if (score >= 550) return { tier: 4, name: 'Subprime Tier 4' };
  return { tier: 5, name: 'Deep Subprime' };
}

// Get points to next tier
function getPointsToNextTier(score) {
  if (!score || score === 0) return null;
  if (score >= 720) return { points: 0, tier: 'Prime', reached: true };
  if (score >= 680) return { points: 720 - score, tier: 'Prime', reached: false };
  if (score >= 630) return { points: 680 - score, tier: 'Near-Prime', reached: false };
  if (score >= 550) return { points: 630 - score, tier: 'Tier 3', reached: false };
  return { points: 550 - score, tier: 'Tier 4', reached: false };
}

export default function ScoreDashboard({ scores = {} }) {
  // Default scores from report data
  const bureauScores = [
    {
      name: 'TransUnion',
      key: 'TU',
      score: scores.TU || scores.transunion || 0,
      color: BUREAU_COLORS.TU
    },
    {
      name: 'Experian',
      key: 'EXP',
      score: scores.EXP || scores.experian || 0,
      color: BUREAU_COLORS.EXP
    },
    {
      name: 'Equifax',
      key: 'EQ',
      score: scores.EQ || scores.equifax || 0,
      color: BUREAU_COLORS.EQ
    }
  ];

  return (
    <Box sx={{ mb: 4 }}>
      <Typography variant="h5" sx={{ mb: 3, fontWeight: 'bold' }}>
        Credit Report Summary
      </Typography>

      {/* Bureau Scores Row */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {bureauScores.map((bureau) => {
          const percentile = getScorePercentile(bureau.score);
          const progressValue = getProgressValue(bureau.score);

          return (
            <Grid item xs={12} sm={4} key={bureau.name}>
              <Card
                sx={{
                  height: '100%',
                  borderRadius: 3,
                  boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                }}
              >
                <CardContent sx={{ p: 3 }}>
                  {/* Header: Bureau name and percentile badge */}
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                    <Typography
                      variant="h6"
                      sx={{
                        fontWeight: 600,
                        color: '#1a365d',
                      }}
                    >
                      {bureau.name}
                    </Typography>
                    {bureau.score > 0 && (
                      <Chip
                        icon={<ArrowUpwardIcon sx={{ fontSize: 14 }} />}
                        label={`${percentile}%`}
                        size="small"
                        sx={{
                          bgcolor: '#dcfce7',
                          color: '#166534',
                          fontWeight: 600,
                          fontSize: '0.75rem',
                          '& .MuiChip-icon': {
                            color: '#166534',
                          },
                        }}
                      />
                    )}
                  </Box>

                  {/* Large Score */}
                  <Typography
                    variant="h2"
                    sx={{
                      fontWeight: 'bold',
                      color: bureau.score > 0 ? '#1a1a1a' : 'text.disabled',
                      mb: 2,
                    }}
                  >
                    {bureau.score > 0 ? bureau.score : '—'}
                  </Typography>

                  {/* Progress Bar */}
                  <LinearProgress
                    variant="determinate"
                    value={progressValue}
                    sx={{
                      height: 8,
                      borderRadius: 4,
                      bgcolor: '#e5e7eb',
                      mb: 2,
                      '& .MuiLinearProgress-bar': {
                        borderRadius: 4,
                        bgcolor: '#22c55e',
                      },
                    }}
                  />

                  {/* Bottom Stats Row */}
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                    <Box>
                      <Typography variant="body2" sx={{ color: 'text.secondary', fontSize: '0.75rem' }}>
                        Estimated Lender Tier
                      </Typography>
                      <Typography variant="body1" sx={{ fontWeight: 'bold', color: '#1a1a1a' }}>
                        {getLenderTier(bureau.score).name}
                      </Typography>
                    </Box>
                    <Box sx={{ textAlign: 'right' }}>
                      {(() => {
                        const goal = getPointsToNextTier(bureau.score);
                        if (!goal) return null;
                        return (
                          <>
                            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                              Goal Progress
                            </Typography>
                            <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#1a1a1a' }}>
                              {goal.reached ? 'Top Tier!' : `${goal.points} pts to ${goal.tier}`}
                            </Typography>
                          </>
                        );
                      })()}
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>

    </Box>
  );
}
