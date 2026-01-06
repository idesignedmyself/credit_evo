/**
 * Credit Engine 2.0 - Document Channel Selector Component
 * Allows user to select document type: Mailed Document, CFPB Complaint, or Litigation Packet
 */
import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  Stack,
} from '@mui/material';
import MailOutlineIcon from '@mui/icons-material/MailOutline';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import GavelIcon from '@mui/icons-material/Gavel';
import { useUIStore } from '../state';

const CHANNEL_CONFIG = {
  MAILED: {
    icon: MailOutlineIcon,
    label: 'Mailed Dispute',
    subtitle: 'Send dispute directly to CRA or Furnisher',
    color: '#1976d2',
    bgColor: '#e3f2fd',
    borderColor: '#1976d2',
    badges: ['FCRA Citations', 'Metro-2', 'MOV Demands'],
  },
  CFPB: {
    icon: AccountBalanceIcon,
    label: 'CFPB Complaint',
    subtitle: 'File complaint with regulator & attach evidence',
    color: '#ed6c02',
    bgColor: '#fff3e0',
    borderColor: '#ed6c02',
    badges: ['Structured Allegations', 'Relief Requested'],
  },
  LITIGATION: {
    icon: GavelIcon,
    label: 'Litigation Packet',
    subtitle: 'Attorney-ready demand & evidence packet',
    color: '#d32f2f',
    bgColor: '#ffebee',
    borderColor: '#d32f2f',
    badges: ['Demand Letter', 'Evidence Index', 'Timeline'],
  },
};

const ToneSelector = () => {
  const {
    documentChannel,
    selectedBureau,
    availableBureaus,
    setDocumentChannel,
  } = useUIStore();

  // Get the bureau display name
  const bureauName = availableBureaus.find(b => b.id === selectedBureau)?.name || selectedBureau;

  return (
    <Paper
      elevation={2}
      sx={{
        p: 3,
        borderRadius: 3,
        boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6">
          Document Type
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Sending to: <strong>{bureauName}</strong>
        </Typography>
      </Box>

      {/* Channel Selection Cards - Equal thirds grid */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 2,
        }}
      >
        {Object.entries(CHANNEL_CONFIG).map(([channel, config]) => {
          const Icon = config.icon;
          const isSelected = documentChannel === channel;

          return (
            <Card
              key={channel}
              elevation={isSelected ? 4 : 1}
              sx={{
                height: '100%',
                border: '2px solid',
                borderColor: isSelected ? config.borderColor : 'transparent',
                bgcolor: isSelected ? config.bgColor : 'background.paper',
                transition: 'all 0.2s ease',
                boxShadow: isSelected ? `0 0 0 2px ${config.color}` : 'none',
              }}
            >
              <CardActionArea
                onClick={() => setDocumentChannel(channel)}
                sx={{ height: '100%' }}
              >
                <CardContent sx={{ textAlign: 'center', py: 3 }}>
                  <Icon
                    sx={{
                      fontSize: 40,
                      color: isSelected ? config.color : 'text.secondary',
                      mb: 1.5,
                    }}
                  />
                  <Typography
                    variant="subtitle1"
                    sx={{
                      fontWeight: 600,
                      color: isSelected ? config.color : 'text.primary',
                      mb: 0.5,
                    }}
                  >
                    {config.label}
                  </Typography>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: 'block', mb: 2, lineHeight: 1.3 }}
                  >
                    {config.subtitle}
                  </Typography>

                  {/* Feature badges */}
                  <Stack
                    direction="row"
                    spacing={0.5}
                    sx={{ flexWrap: 'wrap', justifyContent: 'center', gap: 0.5 }}
                  >
                    {config.badges.map((badge) => (
                      <Chip
                        key={badge}
                        label={badge}
                        size="small"
                        variant={isSelected ? 'filled' : 'outlined'}
                        sx={{
                          fontSize: '0.65rem',
                          height: 20,
                          bgcolor: isSelected ? `${config.color}15` : 'transparent',
                          borderColor: isSelected ? config.color : 'divider',
                          color: isSelected ? config.color : 'text.secondary',
                        }}
                      />
                    ))}
                  </Stack>
                </CardContent>
              </CardActionArea>
            </Card>
          );
        })}
      </Box>

      {/* Selected channel description */}
      <Box sx={{ mt: 3, p: 2, bgcolor: '#f5f5f5', borderRadius: 2 }}>
        <Typography variant="body2" color="text.secondary">
          {documentChannel === 'MAILED' && (
            <>
              <strong>Mailed Dispute</strong> generates a comprehensive FCRA dispute letter with statutory citations,
              Metro-2 compliance requirements, and Method of Verification (MOV) demands.
            </>
          )}
          {documentChannel === 'CFPB' && (
            <>
              <strong>CFPB Complaint</strong> generates a structured complaint for the Consumer Financial Protection Bureau
              with formatted allegations and relief requests.
            </>
          )}
          {documentChannel === 'LITIGATION' && (
            <>
              <strong>Litigation Packet</strong> generates an attorney-ready evidence bundle including demand letter,
              evidence index, and violation timeline.
            </>
          )}
        </Typography>
      </Box>
    </Paper>
  );
};

export default ToneSelector;
