from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

def handle_error(e: Exception, status_code: int = 400):
    """
    Handle exceptions and return user-friendly error messages.
    Logs the original error for debugging while providing safe messages to users.
    """
    # Log the original error for debugging
    logger.error(f"Error occurred: {str(e)}", exc_info=True)

    # Categorize errors and provide user-friendly messages
    error_message = get_friendly_error_message(e, status_code)

    return HTTPException(status_code=status_code, detail=error_message)

def get_friendly_error_message(e: Exception, status_code: int = 400) -> str:
    """
    Convert technical exceptions to user-friendly messages.
    """
    error_str = str(e).lower()

    # Network-related errors
    if any(keyword in error_str for keyword in ['connection', 'network', 'timeout', 'dns', 'unreachable']):
        return "Network connection issue. Please check your internet connection and try again."

    # Database-related errors
    if any(keyword in error_str for keyword in ['database', 'db', 'sql', 'postgres', 'supabase']):
        return "Database temporarily unavailable. Please try again later."

    # Authentication/Authorization errors
    if status_code == 401:
        # Check for specific login error patterns
        if any(keyword in error_str for keyword in ['invalid login credentials', 'email not confirmed', 'invalid credentials']):
            return "Invalid email or password. Please check your credentials and try again."
        elif any(keyword in error_str for keyword in ['user not found', 'no user found']):
            return "No account found with this email. Please sign up first."
        elif any(keyword in error_str for keyword in ['password', 'wrong password']):
            return "Incorrect password. Please try again."
        elif any(keyword in error_str for keyword in ['email not verified', 'email not confirmed']):
            return "Please verify your email address before logging in."
        else:
            return "Authentication failed. Please log in again."

    # Signup errors
    if status_code == 400:
        if any(keyword in error_str for keyword in ['user already registered', 'email already exists', 'already exists']):
            return "An account with this email already exists. Please log in instead."
        elif any(keyword in error_str for keyword in ['weak password', 'password']):
            return "Password is too weak. Please choose a stronger password."
        elif any(keyword in error_str for keyword in ['invalid email']):
            return "Please enter a valid email address."
    if status_code == 403:
        return "You don't have permission to perform this action."

    # Validation errors
    if status_code == 422 or 'validation' in error_str:
        return "Invalid input. Please check your data and try again."

    # Rate limiting
    if status_code == 429:
        return "Too many requests. Please wait a moment and try again."

    # Server errors
    if status_code >= 500:
        return "Server error. Please try again later."

    # OAuth/Google API errors
    if any(keyword in error_str for keyword in ['oauth', 'google', 'token', 'credentials']):
        return "Authentication with external service failed. Please try again."

    # Generic fallback
    return "An unexpected error occurred. Please try again."
