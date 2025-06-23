// Simple content cache invalidation service
class ContentCacheService {
  private subscribers: Set<() => void> = new Set();

  // Subscribe to cache invalidation events
  subscribe(callback: () => void) {
    this.subscribers.add(callback);
    
    // Return unsubscribe function
    return () => {
      this.subscribers.delete(callback);
    };
  }

  // Notify all subscribers that content has changed
  invalidate() {
    this.subscribers.forEach(callback => {
      try {
        callback();
      } catch (error) {
        console.error('Error in cache invalidation callback:', error);
      }
    });
  }
}

export const contentCacheService = new ContentCacheService();
