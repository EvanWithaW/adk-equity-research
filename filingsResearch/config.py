"""
Configuration Module for SEC Filings Research

This module handles configuration settings and API keys for the SEC Filings Research agent.
It loads environment variables and provides a centralized place for configuration settings.
"""

import os
import dotenv
from typing import Dict, Any, Optional

# Load environment variables from .env file
dotenv.load_dotenv()

class Config:
    """
    Configuration class for SEC Filings Research agent.

    This class handles loading and accessing configuration settings and API keys.
    """

    @staticmethod
    def get_api_key(key_name: str) -> Optional[str]:
        """
        Get an API key from environment variables.

        Args:
            key_name (str): The name of the API key to retrieve

        Returns:
            str or None: The API key value, or None if not found
        """
        return os.environ.get(key_name)

    @staticmethod
    def get_google_api_key() -> Optional[str]:
        """
        Get the Google API key from environment variables.

        Returns:
            str or None: The Google API key, or None if not found
        """
        return Config.get_api_key("GOOGLE_API_KEY")

    @staticmethod
    def get_seeking_alpha_api_key() -> Optional[str]:
        """
        Get the Seeking Alpha API key from environment variables.

        Returns:
            str or None: The Seeking Alpha API key, or None if not found
        """
        return Config.get_api_key("SEEKING_ALPHA_API_KEY")

    @staticmethod
    def get_sec_user_agent() -> str:
        """
        Get the User-Agent string for SEC API requests.

        Returns:
            str: The User-Agent string
        """
        # This should be customized with your information as per SEC requirements
        return os.environ.get("SEC_USER_AGENT", "Educational Project Evan Weidner hi@evanweidner.com")

    @staticmethod
    def get_alpha_vantage_api_key() -> Optional[str]:
        """
        Get the Alpha Vantage API key from environment variables.

        Returns:
            str or None: The Alpha Vantage API key, or None if not found
        """
        return Config.get_api_key("ALPHA_VANTAGE_API_KEY")

    @staticmethod
    def validate_required_keys() -> Dict[str, bool]:
        """
        Validate that all required API keys are present.

        Returns:
            dict: A dictionary of API key names and their presence status
        """
        required_keys = ["GOOGLE_API_KEY", "ALPHA_VANTAGE_API_KEY"]
        return {key: Config.get_api_key(key) is not None for key in required_keys}

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """
        Get all configuration settings.

        Returns:
            dict: A dictionary of all configuration settings
        """
        return {
            "google_api_key_present": Config.get_google_api_key() is not None,
            "alpha_vantage_api_key_present": Config.get_alpha_vantage_api_key() is not None,
            "sec_user_agent": Config.get_sec_user_agent(),
        }
