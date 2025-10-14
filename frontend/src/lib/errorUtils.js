import { toast } from "sonner";

/**
 * Maps technical errors to user-friendly messages.
 * @param {Error|Object} error - The error object from axios or other sources.
 * @returns {string} - User-friendly error message.
 */
export function getFriendlyErrorMessage(error) {
  // Handle axios errors
  if (error.response) {
    const status = error.response.status;
    const data = error.response.data;

    // Specific status codes
    switch (status) {
      case 400:
        // For signup endpoint, show specific error messages
        if (data?.detail && (
          data.detail.includes("already exists") ||
          data.detail.includes("Please log in instead") ||
          data.detail.includes("too weak") ||
          data.detail.includes("valid email")
        )) {
          return data.detail;
        }
        return data?.detail || "Invalid request. Please check your input and try again.";
      case 401:
        // For login endpoint, show the specific error message from backend
        if (data?.detail && (
          data.detail.includes("Invalid email or password") ||
          data.detail.includes("No account found") ||
          data.detail.includes("Incorrect password") ||
          data.detail.includes("Please verify your email")
        )) {
          return data.detail;
        }
        return "Your session has expired. Please log in again.";
      case 403:
        return "You don't have permission to perform this action.";
      case 404:
        return "The requested resource was not found.";
      case 409:
        return "This action conflicts with existing data. Please try again.";
      case 422:
        return "Validation failed. Please check your input.";
      case 429:
        return "Too many requests. Please wait a moment and try again.";
      case 500:
        return "Server error. Please try again later.";
      case 502:
      case 503:
      case 504:
        return "Service temporarily unavailable. Please try again later.";
      default:
        return data?.detail || `Request failed with status ${status}.`;
    }
  } else if (error.request) {
    // Network error (no response received)
    if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
      return "Request timed out. Please check your connection and try again.";
    }
    return "Network error. Please check your internet connection and try again.";
  } else {
    // Other errors
    if (error.message) {
      // Check for specific error messages
      const msg = error.message.toLowerCase();
      if (msg.includes('network') || msg.includes('connection')) {
        return "Network connection issue. Please check your internet and try again.";
      }
      if (msg.includes('timeout')) {
        return "Request timed out. Please try again.";
      }
      if (msg.includes('cancel')) {
        return "Request was cancelled.";
      }
    }
    return error.message || "An unexpected error occurred.";
  }
}

/**
 * Shows a toast notification with a user-friendly error message.
 * @param {Error|Object} error - The error object.
 * @param {string} fallbackMessage - Optional fallback message.
 */
export function showErrorToast(error, fallbackMessage = "Something went wrong. Please try again.") {
  const message = getFriendlyErrorMessage(error) || fallbackMessage;
  toast.error(message);
}

/**
 * Shows a success toast.
 * @param {string} message - The success message.
 */
export function showSuccessToast(message) {
  toast.success(message);
}

/**
 * Shows an info toast.
 * @param {string} message - The info message.
 */
export function showInfoToast(message) {
  toast.info(message);
}
