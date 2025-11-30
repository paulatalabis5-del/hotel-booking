document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Rating stars functionality
    const ratingStars = document.querySelectorAll('.rating-star');
    if (ratingStars.length > 0) {
        ratingStars.forEach(star => {
            star.addEventListener('click', function() {
                const value = this.getAttribute('data-value');
                document.getElementById('rating-value').value = value;
                
                // Update stars display
                ratingStars.forEach(s => {
                    const starValue = s.getAttribute('data-value');
                    if (starValue <= value) {
                        s.classList.add('active');
                        s.classList.remove('far');
                        s.classList.add('fas');
                    } else {
                        s.classList.remove('active');
                        s.classList.remove('fas');
                        s.classList.add('far');
                    }
                });
            });
        });
    }

    // Get notification count and load notifications
    function updateNotificationCount() {
        if (document.getElementById('notification-badge')) {
            fetch('/api/notifications/count')
                .then(response => response.json())
                .then(data => {
                    const badge = document.getElementById('notification-badge');
                    if (data.count > 0) {
                        badge.textContent = data.count;
                        badge.style.display = 'block';
                    } else {
                        badge.style.display = 'none';
                    }
                })
                .catch(error => console.error('Error fetching notification count:', error));
        }
    }

    // Load notifications into modal
    function loadNotifications() {
        fetch('/api/notifications')
            .then(response => response.json())
            .then(data => {
                const container = document.getElementById('notifications-container');
                if (data.notifications.length === 0) {
                    container.innerHTML = '<div class="alert alert-info">You have no notifications.</div>';
                    return;
                }

                let html = '';
                data.notifications.forEach(notification => {
                    html += `
                        <div class="notification-item ${notification.is_read ? '' : 'unread'} mb-3 p-3 border rounded">
                            <div class="d-flex justify-content-between align-items-start">
                                <h6 class="mb-1">${notification.title}</h6>
                                <small class="text-muted">${new Date(notification.created_at).toLocaleString()}</small>
                            </div>
                            <p class="mb-1">${notification.message}</p>
                            ${!notification.is_read ? '<span class="badge bg-primary">New</span>' : ''}
                        </div>
                    `;
                });
                container.innerHTML = html;
            })
            .catch(error => console.error('Error loading notifications:', error));
    }

    // Handle notification bell click
    const notificationBell = document.getElementById('notification-bell');
    if (notificationBell) {
        notificationBell.addEventListener('click', function(e) {
            e.preventDefault();
            loadNotifications();
        });
    }

    // Handle mark all as read
    const markAllReadBtn = document.getElementById('mark-all-read');
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', function() {
            fetch('/api/notifications/mark-all-read', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    loadNotifications();
                    updateNotificationCount();
                }
            })
            .catch(error => console.error('Error marking notifications as read:', error));
        });
    }

    // Call initially and then every minute
    updateNotificationCount();
    setInterval(updateNotificationCount, 60000);

    // Date validation for booking form
    const checkInInput = document.getElementById('check-in-date');
    const checkOutInput = document.getElementById('check-out-date');
    
    if (checkInInput && checkOutInput) {
        // Set min date to today
        const today = new Date();
        const todayStr = today.toISOString().split('T')[0];
        checkInInput.min = todayStr;
        
        checkInInput.addEventListener('change', function() {
            // Set min check-out date to check-in date + 1 day
            const checkInDate = new Date(this.value);
            const minCheckOutDate = new Date(checkInDate);
            minCheckOutDate.setDate(minCheckOutDate.getDate() + 1);
            checkOutInput.min = minCheckOutDate.toISOString().split('T')[0];
            
            // If check-out date is before new min, reset it
            if (new Date(checkOutInput.value) <= checkInDate) {
                checkOutInput.value = minCheckOutDate.toISOString().split('T')[0];
            }
        });
    }

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // Show current year in footer copyright
    const yearSpan = document.getElementById('current-year');
    if (yearSpan) {
        yearSpan.textContent = new Date().getFullYear();
    }
});
