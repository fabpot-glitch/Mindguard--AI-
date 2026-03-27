import { useState, useCallback, useEffect } from 'react';

/**
 * Custom hook for managing interventions
 * @param {Object} lastMessage - Last WebSocket message
 * @param {Function} sendMessage - Function to send WebSocket messages
 * @returns {Object} Intervention state and methods
 */
export const useIntervention = (lastMessage, sendMessage) => {
  const [activeIntervention, setActiveIntervention] = useState(null);
  const [interventionHistory, setInterventionHistory] = useState([]);
  const [interventionStats, setInterventionStats] = useState({
    total: 0,
    completed: 0,
    dismissed: 0,
    byType: {},
    today: 0
  });

  const MAX_HISTORY = 50;

  // Listen for interventions from WebSocket
  useEffect(() => {
    if (!lastMessage) return;
    
    if (lastMessage.type === 'intervention' && lastMessage.data) {
      handleNewIntervention(lastMessage.data);
    }
  }, [lastMessage]);

  // Handle new intervention
  const handleNewIntervention = useCallback((intervention) => {
    setActiveIntervention(intervention);
    
    setInterventionHistory(prev => {
      const newHistory = [intervention, ...prev].slice(0, MAX_HISTORY);
      return newHistory;
    });
    
    // Update stats
    setInterventionStats(prev => {
      const type = intervention.type;
      const today = new Date().toDateString();
      
      return {
        ...prev,
        total: prev.total + 1,
        byType: {
          ...prev.byType,
          [type]: (prev.byType[type] || 0) + 1
        },
        today: new Date(intervention.timestamp).toDateString() === today 
          ? prev.today + 1 
          : prev.today
      };
    });
    
    // Send acknowledgment
    if (sendMessage) {
      sendMessage({
        type: 'intervention_received',
        intervention_id: intervention.id,
        timestamp: new Date().toISOString()
      });
    }
  }, [sendMessage]);

  // Dismiss active intervention
  const dismissIntervention = useCallback((interventionId) => {
    if (activeIntervention && activeIntervention.id === interventionId) {
      setActiveIntervention(null);
      
      // Update history
      setInterventionHistory(prev => 
        prev.map(i => 
          i.id === interventionId 
            ? { ...i, status: 'dismissed', dismissedAt: new Date().toISOString() }
            : i
        )
      );
      
      // Update stats
      setInterventionStats(prev => ({
        ...prev,
        dismissed: prev.dismissed + 1
      }));
      
      // Send dismissal to server
      if (sendMessage) {
        sendMessage({
          type: 'intervention_dismissed',
          intervention_id: interventionId,
          timestamp: new Date().toISOString()
        });
      }
    }
  }, [activeIntervention, sendMessage]);

  // Complete active intervention
  const completeIntervention = useCallback((interventionId) => {
    if (activeIntervention && activeIntervention.id === interventionId) {
      setActiveIntervention(null);
      
      // Update history
      setInterventionHistory(prev => 
        prev.map(i => 
          i.id === interventionId 
            ? { ...i, status: 'completed', completedAt: new Date().toISOString() }
            : i
        )
      );
      
      // Update stats
      setInterventionStats(prev => ({
        ...prev,
        completed: prev.completed + 1
      }));
      
      // Send completion to server
      if (sendMessage) {
        sendMessage({
          type: 'intervention_completed',
          intervention_id: interventionId,
          timestamp: new Date().toISOString()
        });
      }
    }
  }, [activeIntervention, sendMessage]);

  // Snooze intervention
  const snoozeIntervention = useCallback((interventionId, minutes = 15) => {
    if (activeIntervention && activeIntervention.id === interventionId) {
      setActiveIntervention(null);
      
      // Update history
      setInterventionHistory(prev => 
        prev.map(i => 
          i.id === interventionId 
            ? { ...i, status: 'snoozed', snoozedUntil: new Date(Date.now() + minutes * 60000).toISOString() }
            : i
        )
      );
      
      // Send snooze to server
      if (sendMessage) {
        sendMessage({
          type: 'intervention_snoozed',
          intervention_id: interventionId,
          snooze_minutes: minutes,
          timestamp: new Date().toISOString()
        });
      }
      
      // Set timeout to remind again
      setTimeout(() => {
        // Re-trigger the same intervention
        handleNewIntervention(activeIntervention);
      }, minutes * 60000);
    }
  }, [activeIntervention, sendMessage, handleNewIntervention]);

  // Get intervention by ID
  const getIntervention = useCallback((interventionId) => {
    if (activeIntervention && activeIntervention.id === interventionId) {
      return activeIntervention;
    }
    return interventionHistory.find(i => i.id === interventionId);
  }, [activeIntervention, interventionHistory]);

  // Get interventions by type
  const getInterventionsByType = useCallback((type) => {
    return interventionHistory.filter(i => i.type === type);
  }, [interventionHistory]);

  // Get interventions by date range
  const getInterventionsByDateRange = useCallback((startDate, endDate) => {
    return interventionHistory.filter(i => {
      const date = new Date(i.timestamp);
      return date >= startDate && date <= endDate;
    });
  }, [interventionHistory]);

  // Calculate effectiveness score
  const getEffectivenessScore = useCallback(() => {
    if (interventionStats.total === 0) return 0;
    
    const completed = interventionStats.completed;
    const total = interventionStats.total;
    
    return Math.round((completed / total) * 100);
  }, [interventionStats]);

  // Get response time stats
  const getResponseTimeStats = useCallback(() => {
    const responseTimes = interventionHistory
      .filter(i => i.completedAt)
      .map(i => new Date(i.completedAt) - new Date(i.timestamp));
    
    if (responseTimes.length === 0) return null;
    
    return {
      avg: Math.round(responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length / 1000),
      min: Math.round(Math.min(...responseTimes) / 1000),
      max: Math.round(Math.max(...responseTimes) / 1000)
    };
  }, [interventionHistory]);

  // Clear history
  const clearHistory = useCallback(() => {
    setInterventionHistory([]);
    setInterventionStats({
      total: 0,
      completed: 0,
      dismissed: 0,
      byType: {},
      today: 0
    });
  }, []);

  // Format intervention for display
  const formatIntervention = useCallback((intervention) => {
    const getIcon = (type) => {
      switch (type) {
        case 'break_reminder': return '☕';
        case 'breathing_exercise': return '🧘';
        case 'hydration_reminder': return '💧';
        case 'task_switch_suggestion': return '🔄';
        case 'stretch_reminder': return '🤸';
        case 'focus_recovery': return '🎯';
        case 'energy_boost': return '⚡';
        default: return '🔔';
      }
    };

    const getColor = (level) => {
      switch (level) {
        case 'critical': return '#F44336';
        case 'warning': return '#FF9800';
        case 'suggestion': return '#4CAF50';
        default: return '#4A90E2';
      }
    };

    return {
      ...intervention,
      icon: getIcon(intervention.type),
      color: getColor(intervention.level),
      timeAgo: getTimeAgo(new Date(intervention.timestamp)),
      formattedDuration: formatDuration(intervention.duration_seconds)
    };
  }, []);

  // Helper: get time ago string
  const getTimeAgo = (date) => {
    const seconds = Math.floor((new Date() - date) / 1000);
    
    const intervals = {
      year: 31536000,
      month: 2592000,
      week: 604800,
      day: 86400,
      hour: 3600,
      minute: 60
    };
    
    for (const [unit, secondsInUnit] of Object.entries(intervals)) {
      const interval = Math.floor(seconds / secondsInUnit);
      if (interval >= 1) {
        return `${interval} ${unit}${interval === 1 ? '' : 's'} ago`;
      }
    }
    
    return 'just now';
  };

  // Helper: format duration
  const formatDuration = (seconds) => {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ${minutes % 60}m`;
  };

  return {
    activeIntervention,
    interventionHistory,
    interventionStats,
    dismissIntervention,
    completeIntervention,
    snoozeIntervention,
    getIntervention,
    getInterventionsByType,
    getInterventionsByDateRange,
    getEffectivenessScore,
    getResponseTimeStats,
    clearHistory,
    formatIntervention
  };
};

export default useIntervention;