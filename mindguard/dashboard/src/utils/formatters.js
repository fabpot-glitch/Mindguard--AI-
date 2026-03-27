/**
 * Formatting utilities for MindGuard AI dashboard
 */

/**
 * Format time in seconds to HH:MM:SS
 * @param {number} seconds - Time in seconds
 * @param {boolean} includeHours - Whether to include hours
 * @returns {string} Formatted time string
 */
export const formatTime = (seconds, includeHours = true) => {
  if (seconds === undefined || seconds === null) return '00:00';
  
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  
  if (includeHours && hours > 0) {
    return `${hours.toString().padStart(2, '0')}:${minutes
      .toString()
      .padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  
  return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

/**
 * Format date to relative time (e.g., "5 minutes ago")
 * @param {string|Date} date - Date to format
 * @returns {string} Relative time string
 */
export const formatRelativeTime = (date) => {
  const now = new Date();
  const then = new Date(date);
  const seconds = Math.floor((now - then) / 1000);
  
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

/**
 * Format date to readable string
 * @param {string|Date} date - Date to format
 * @param {Object} options - Intl.DateTimeFormat options
 * @returns {string} Formatted date string
 */
export const formatDate = (date, options = {}) => {
  const defaultOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  };
  
  const mergedOptions = { ...defaultOptions, ...options };
  
  return new Date(date).toLocaleDateString('en-US', mergedOptions);
};

/**
 * Format percentage
 * @param {number} value - Value between 0-1
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted percentage
 */
export const formatPercentage = (value, decimals = 0) => {
  if (value === undefined || value === null) return '0%';
  return `${(value * 100).toFixed(decimals)}%`;
};

/**
 * Format number with commas
 * @param {number} num - Number to format
 * @returns {string} Formatted number
 */
export const formatNumber = (num) => {
  if (num === undefined || num === null) return '0';
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};

/**
 * Format duration in human readable form
 * @param {number} seconds - Duration in seconds
 * @returns {string} Human readable duration
 */
export const formatDuration = (seconds) => {
  if (!seconds || seconds < 0) return '0s';
  
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  
  const parts = [];
  
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);
  
  return parts.join(' ');
};

/**
 * Format file size
 * @param {number} bytes - Size in bytes
 * @returns {string} Formatted file size
 */
export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B';
  
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  
  return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${units[i]}`;
};

/**
 * Format intervention type to readable string
 * @param {string} type - Intervention type
 * @returns {string} Readable intervention type
 */
export const formatInterventionType = (type) => {
  const typeMap = {
    break_reminder: 'Break Reminder',
    breathing_exercise: 'Breathing Exercise',
    hydration_reminder: 'Hydration Reminder',
    task_switch_suggestion: 'Task Switch',
    stretch_reminder: 'Stretch Reminder',
    focus_recovery: 'Focus Recovery',
    energy_boost: 'Energy Boost',
    mindfulness_moment: 'Mindfulness'
  };
  
  return typeMap[type] || type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

/**
 * Format metric name to readable string
 * @param {string} metric - Metric name
 * @returns {string} Readable metric name
 */
export const formatMetricName = (metric) => {
  const metricMap = {
    fatigue: 'Fatigue Level',
    stress: 'Stress Level',
    attention: 'Attention',
    cognitive_load: 'Cognitive Load',
    confidence: 'Confidence',
    cognitiveLoad: 'Cognitive Load'
  };
  
  return metricMap[metric] || metric.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

/**
 * Format trend value
 * @param {number} trend - Trend value
 * @returns {Object} Formatted trend with icon and color
 */
export const formatTrend = (trend) => {
  if (trend === undefined || trend === null) {
    return { icon: '→', color: '#a0a0a0', text: 'Stable' };
  }
  
  if (trend > 0.05) {
    return { icon: '↑', color: '#F44336', text: 'Increasing' };
  } else if (trend < -0.05) {
    return { icon: '↓', color: '#4CAF50', text: 'Decreasing' };
  } else {
    return { icon: '→', color: '#FFC107', text: 'Stable' };
  }
};

/**
 * Format confidence level
 * @param {number} confidence - Confidence value 0-1
 * @returns {Object} Formatted confidence with label
 */
export const formatConfidence = (confidence) => {
  if (confidence >= 0.8) return { label: 'High', color: '#4CAF50' };
  if (confidence >= 0.6) return { label: 'Medium', color: '#FFC107' };
  if (confidence >= 0.4) return { label: 'Low', color: '#FF9800' };
  return { label: 'Very Low', color: '#F44336' };
};

/**
 * Format list of items
 * @param {Array} items - Items to format
 * @param {string} separator - Separator between items
 * @returns {string} Formatted list
 */
export const formatList = (items, separator = ', ') => {
  if (!items || items.length === 0) return '';
  if (items.length === 1) return items[0];
  if (items.length === 2) return `${items[0]} and ${items[1]}`;
  
  const last = items.pop();
  return `${items.join(separator)} and ${last}`;
};

/**
 * Truncate text with ellipsis
 * @param {string} text - Text to truncate
 * @param {number} length - Maximum length
 * @returns {string} Truncated text
 */
export const truncateText = (text, length = 50) => {
  if (!text || text.length <= length) return text;
  return text.substring(0, length) + '...';
};

/**
 * Format phone number
 * @param {string} phone - Phone number
 * @returns {string} Formatted phone number
 */
export const formatPhone = (phone) => {
  const cleaned = ('' + phone).replace(/\D/g, '');
  const match = cleaned.match(/^(\d{3})(\d{3})(\d{4})$/);
  
  if (match) {
    return '(' + match[1] + ') ' + match[2] + '-' + match[3];
  }
  
  return phone;
};

export default {
  formatTime,
  formatRelativeTime,
  formatDate,
  formatPercentage,
  formatNumber,
  formatDuration,
  formatFileSize,
  formatInterventionType,
  formatMetricName,
  formatTrend,
  formatConfidence,
  formatList,
  truncateText,
  formatPhone
};