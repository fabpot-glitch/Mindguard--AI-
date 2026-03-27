/**
 * Color utilities for MindGuard AI dashboard
 */

// Color palettes
export const colors = {
  // Primary metrics
  fatigue: '#F44336',
  stress: '#FF9800',
  attention: '#4CAF50',
  cognitiveLoad: '#9C27B0',
  confidence: '#4A90E2',
  
  // Alert levels
  critical: '#F44336',
  warning: '#FF9800',
  info: '#4A90E2',
  success: '#4CAF50',
  
  // UI colors
  background: '#0a0b0e',
  surface: '#1a1c21',
  surfaceLight: '#2a2c33',
  text: '#e0e0e0',
  textSecondary: '#a0a0a0',
  border: '#3a3f4b',
  
  // Gradients
  gradientStart: '#4A90E2',
  gradientEnd: '#9C27B0'
};

/**
 * Get color for a specific metric
 * @param {string} metric - Metric name
 * @returns {string} Color hex code
 */
export const getMetricColor = (metric) => {
  const metricColors = {
    fatigue: colors.fatigue,
    stress: colors.stress,
    attention: colors.attention,
    cognitive_load: colors.cognitiveLoad,
    cognitiveLoad: colors.cognitiveLoad,
    confidence: colors.confidence
  };
  
  return metricColors[metric] || colors.info;
};

/**
 * Get color based on value and thresholds
 * @param {number} value - Value between 0-1
 * @param {Object} thresholds - Threshold object {low, medium, high}
 * @param {boolean} reverse - Reverse the color scale
 * @returns {string} Color hex code
 */
export const getThresholdColor = (value, thresholds, reverse = false) => {
  if (reverse) {
    if (value <= thresholds.low) return colors.success;
    if (value <= thresholds.medium) return colors.warning;
    if (value <= thresholds.high) return colors.warning;
    return colors.critical;
  } else {
    if (value <= thresholds.low) return colors.success;
    if (value <= thresholds.medium) return colors.warning;
    if (value <= thresholds.high) return colors.warning;
    return colors.critical;
  }
};

/**
 * Get color for alert level
 * @param {string} level - Alert level
 * @returns {string} Color hex code
 */
export const getAlertLevelColor = (level) => {
  const levelColors = {
    critical: colors.critical,
    warning: colors.warning,
    info: colors.info,
    success: colors.success,
    suggestion: colors.info
  };
  
  return levelColors[level] || colors.info;
};

/**
 * Generate gradient CSS string
 * @param {string} startColor - Start color
 * @param {string} endColor - End color
 * @param {string} direction - Gradient direction
 * @returns {string} CSS gradient string
 */
export const getGradient = (startColor = colors.gradientStart, endColor = colors.gradientEnd, direction = 'to right') => {
  return `linear-gradient(${direction}, ${startColor}, ${endColor})`;
};

/**
 * Lighten a color
 * @param {string} color - Hex color
 * @param {number} percent - Percent to lighten (0-100)
 * @returns {string} Lightened hex color
 */
export const lightenColor = (color, percent) => {
  const num = parseInt(color.replace('#', ''), 16);
  const amt = Math.round(2.55 * percent);
  const R = (num >> 16) + amt;
  const G = (num >> 8 & 0x00FF) + amt;
  const B = (num & 0x0000FF) + amt;
  
  return '#' + (
    0x1000000 +
    (R < 255 ? (R < 1 ? 0 : R) : 255) * 0x10000 +
    (G < 255 ? (G < 1 ? 0 : G) : 255) * 0x100 +
    (B < 255 ? (B < 1 ? 0 : B) : 255)
  ).toString(16).slice(1);
};

/**
 * Darken a color
 * @param {string} color - Hex color
 * @param {number} percent - Percent to darken (0-100)
 * @returns {string} Darkened hex color
 */
export const darkenColor = (color, percent) => {
  return lightenColor(color, -percent);
};

/**
 * Convert hex to rgba
 * @param {string} hex - Hex color
 * @param {number} alpha - Alpha value (0-1)
 * @returns {string} RGBA string
 */
export const hexToRgba = (hex, alpha = 1) => {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

/**
 * Get contrasting text color (black or white) based on background
 * @param {string} backgroundColor - Hex background color
 * @returns {string} '#000000' or '#FFFFFF'
 */
export const getContrastColor = (backgroundColor) => {
  const hex = backgroundColor.replace('#', '');
  const r = parseInt(hex.substr(0, 2), 16);
  const g = parseInt(hex.substr(2, 2), 16);
  const b = parseInt(hex.substr(4, 2), 16);
  
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  
  return luminance > 0.5 ? '#000000' : '#FFFFFF';
};

/**
 * Generate color scale for heatmap
 * @param {number} value - Value between 0-1
 * @returns {string} Color hex code
 */
export const getHeatmapColor = (value) => {
  // Red for high values, green for low values
  const r = Math.min(255, Math.floor(255 * value * 2));
  const g = Math.min(255, Math.floor(255 * (1 - value) * 2));
  const b = 0;
  
  return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
};

/**
 * Get status color based on cognitive state
 * @param {Object} state - Cognitive state
 * @returns {Object} Status colors
 */
export const getStatusColors = (state) => {
  if (!state) return {};
  
  return {
    fatigue: getThresholdColor(state.fatigue, { low: 0.3, medium: 0.6, high: 0.8 }),
    stress: getThresholdColor(state.stress, { low: 0.3, medium: 0.5, high: 0.7 }),
    attention: getThresholdColor(state.attention, { low: 0.3, medium: 0.6, high: 0.8 }, true),
    cognitive_load: getThresholdColor(state.cognitive_load, { low: 0.4, medium: 0.6, high: 0.8 })
  };
};

export default {
  colors,
  getMetricColor,
  getThresholdColor,
  getAlertLevelColor,
  getGradient,
  lightenColor,
  darkenColor,
  hexToRgba,
  getContrastColor,
  getHeatmapColor,
  getStatusColors
};