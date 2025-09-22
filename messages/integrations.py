"""
Integration services for naebak-messaging-service
Handles communication with other naebak services
"""

import requests
import logging
from django.conf import settings
from django.core.cache import cache
from typing import Dict, List, Optional, Any
import json

logger = logging.getLogger(__name__)


class ContentServiceIntegration:
    """Integration with naebak-content-service"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'CONTENT_SERVICE_URL', 'http://localhost:8001')
        self.timeout = getattr(settings, 'SERVICE_TIMEOUT', 10)
        self.cache_timeout = getattr(settings, 'CACHE_TIMEOUT', 300)  # 5 minutes
    
    def _make_request(self, endpoint: str, method: str = 'GET', data: Dict = None) -> Optional[Dict]:
        """Make HTTP request to content service"""
        try:
            url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'naebak-messaging-service/1.0'
            }
            
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=self.timeout)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=self.timeout)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout when calling content service: {endpoint}")
            return None
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error when calling content service: {endpoint}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error when calling content service: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error when calling content service: {e}")
            return None
    
    def get_representative_by_id(self, representative_id: int) -> Optional[Dict]:
        """Get representative details by ID"""
        cache_key = f"representative_{representative_id}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        data = self._make_request(f"representatives/{representative_id}/")
        if data:
            cache.set(cache_key, data, self.cache_timeout)
        
        return data
    
    def get_representative_by_slug(self, slug: str) -> Optional[Dict]:
        """Get representative details by slug"""
        cache_key = f"representative_slug_{slug}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        data = self._make_request(f"representatives/{slug}/")
        if data:
            cache.set(cache_key, data, self.cache_timeout)
        
        return data
    
    def search_representatives(self, filters: Dict = None) -> List[Dict]:
        """Search representatives with filters"""
        cache_key = f"representatives_search_{hash(str(sorted((filters or {}).items())))}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        endpoint = "representatives/"
        if filters:
            query_params = "&".join([f"{k}={v}" for k, v in filters.items() if v])
            if query_params:
                endpoint += f"?{query_params}"
        
        data = self._make_request(endpoint)
        if data and 'results' in data:
            results = data['results']
            cache.set(cache_key, results, self.cache_timeout)
            return results
        
        return []
    
    def get_governorates(self) -> List[Dict]:
        """Get list of governorates"""
        cache_key = "governorates_list"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        data = self._make_request("governorates/")
        if data and 'results' in data:
            results = data['results']
            cache.set(cache_key, results, self.cache_timeout * 4)  # Cache longer
            return results
        
        return []
    
    def get_districts_by_governorate(self, governorate_id: int) -> List[Dict]:
        """Get districts by governorate"""
        cache_key = f"districts_gov_{governorate_id}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        data = self._make_request(f"districts/?governorate={governorate_id}")
        if data and 'results' in data:
            results = data['results']
            cache.set(cache_key, results, self.cache_timeout * 2)
            return results
        
        return []
    
    def get_political_parties(self) -> List[Dict]:
        """Get list of political parties"""
        cache_key = "political_parties_list"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        data = self._make_request("parties/")
        if data and 'results' in data:
            results = data['results']
            cache.set(cache_key, results, self.cache_timeout * 4)  # Cache longer
            return results
        
        return []
    
    def validate_representative_exists(self, representative_id: int) -> bool:
        """Validate that a representative exists"""
        representative = self.get_representative_by_id(representative_id)
        return representative is not None
    
    def get_representative_contact_info(self, representative_id: int) -> Optional[Dict]:
        """Get representative contact information for messaging"""
        representative = self.get_representative_by_id(representative_id)
        if not representative:
            return None
        
        return {
            'id': representative.get('id'),
            'name': representative.get('name'),
            'slug': representative.get('slug'),
            'governorate': representative.get('governorate_name'),
            'district': representative.get('district_name'),
            'party': representative.get('party_name'),
            'avatar': representative.get('avatar'),
            'is_featured': representative.get('is_featured', False),
            'rating': representative.get('average_rating', 0),
            'complaints_resolved': representative.get('complaints_resolved', 0),
            'complaints_received': representative.get('complaints_received', 0)
        }
    
    def increment_message_count(self, representative_id: int) -> bool:
        """Increment message count for representative statistics"""
        try:
            data = self._make_request(
                f"representatives/{representative_id}/increment_messages/",
                method='POST'
            )
            return data is not None
        except Exception as e:
            logger.error(f"Failed to increment message count: {e}")
            return False


class AuthServiceIntegration:
    """Integration with naebak-auth-service"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'AUTH_SERVICE_URL', 'http://localhost:8002')
        self.timeout = getattr(settings, 'SERVICE_TIMEOUT', 10)
    
    def _make_request(self, endpoint: str, method: str = 'GET', data: Dict = None, headers: Dict = None) -> Optional[Dict]:
        """Make HTTP request to auth service"""
        try:
            url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
            default_headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'naebak-messaging-service/1.0'
            }
            
            if headers:
                default_headers.update(headers)
            
            if method.upper() == 'GET':
                response = requests.get(url, headers=default_headers, timeout=self.timeout)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=default_headers, json=data, timeout=self.timeout)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Error calling auth service: {e}")
            return None
    
    def validate_token(self, token: str) -> Optional[Dict]:
        """Validate JWT token with auth service"""
        headers = {'Authorization': f'Bearer {token}'}
        return self._make_request('auth/validate/', headers=headers)
    
    def get_user_profile(self, user_id: int, token: str) -> Optional[Dict]:
        """Get user profile from auth service"""
        headers = {'Authorization': f'Bearer {token}'}
        return self._make_request(f'users/{user_id}/', headers=headers)


class ServiceIntegrationManager:
    """Manager for all service integrations"""
    
    def __init__(self):
        self.content_service = ContentServiceIntegration()
        self.auth_service = AuthServiceIntegration()
    
    def get_messaging_context(self, user_id: int, representative_id: int = None) -> Dict[str, Any]:
        """Get complete context for messaging interface"""
        context = {
            'governorates': self.content_service.get_governorates(),
            'political_parties': self.content_service.get_political_parties(),
            'representatives': []
        }
        
        if representative_id:
            representative = self.content_service.get_representative_contact_info(representative_id)
            if representative:
                context['selected_representative'] = representative
        
        # Get featured representatives for quick access
        featured_reps = self.content_service.search_representatives({'is_featured': True})
        context['featured_representatives'] = featured_reps[:10]  # Limit to 10
        
        return context
    
    def validate_conversation_participants(self, citizen_id: int, representative_id: int) -> Dict[str, bool]:
        """Validate that conversation participants are valid"""
        return {
            'citizen_valid': True,  # Assume valid since they're authenticated
            'representative_valid': self.content_service.validate_representative_exists(representative_id)
        }
    
    def get_conversation_metadata(self, representative_id: int) -> Dict[str, Any]:
        """Get metadata for conversation with representative"""
        representative = self.content_service.get_representative_contact_info(representative_id)
        if not representative:
            return {}
        
        return {
            'representative_name': representative['name'],
            'representative_governorate': representative['governorate'],
            'representative_district': representative['district'],
            'representative_party': representative['party'],
            'representative_rating': representative['rating'],
            'representative_avatar': representative['avatar'],
            'is_featured': representative['is_featured']
        }


# Global instance
integration_manager = ServiceIntegrationManager()
