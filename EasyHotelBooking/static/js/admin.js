document.addEventListener('DOMContentLoaded', function() {
    // Let's fix the show details functionality first
    setupBookingDetails();
    setupCancelBooking();
    setupConfirmBooking();
    setupRatingReplies();
    setupRatingDetails();
    
    // Elements - we'll keep these for other functionality
    const pendingBookingsTable = document.getElementById('pending-bookings');
    const confirmedBookingsTable = document.getElementById('confirmed-bookings');
    const cancelledBookingsTable = document.getElementById('cancelled-bookings');
    const ratingsTable = document.getElementById('ratings-table');
    
    // Toggle booking details
    function setupBookingDetails() {
        document.querySelectorAll('.booking-details-btn').forEach(button => {
            button.addEventListener('click', function() {
                const bookingId = this.dataset.bookingId;
                const detailsRow = document.getElementById(`booking-details-${bookingId}`);
                
                if (detailsRow.style.display === 'none' || !detailsRow.style.display) {
                    detailsRow.style.display = 'table-row';
                    this.textContent = 'Hide Details';
                } else {
                    detailsRow.style.display = 'none';
                    this.textContent = 'Show Details';
                }
            });
        });
    }
    
    // Handle cancel booking confirmation
    function setupCancelBooking() {
        document.querySelectorAll('.cancel-booking-btn').forEach(button => {
            button.addEventListener('click', function() {
                const bookingId = this.dataset.bookingId;
                const cancelForm = document.getElementById(`cancel-form-${bookingId}`);
                const cancelReason = document.getElementById(`cancel-reason-${bookingId}`);
                
                // Check if a reason is provided
                if (!cancelReason.value.trim()) {
                    alert('Please provide a cancellation reason');
                    return;
                }
                
                // Confirm cancellation
                if (confirm('Are you sure you want to cancel this booking? This action cannot be undone.')) {
                    cancelForm.submit();
                }
            });
        });
    }
    
    // Handle confirm booking confirmation
    function setupConfirmBooking() {
        document.querySelectorAll('.confirm-booking-btn').forEach(button => {
            button.addEventListener('click', function() {
                const bookingId = this.dataset.bookingId;
                const confirmForm = document.getElementById(`confirm-form-${bookingId}`);
                
                // Confirm confirmation
                if (confirm('Are you sure you want to confirm this booking?')) {
                    confirmForm.submit();
                }
            });
        });
    }
    
    // Handle rating replies
    function setupRatingReplies() {
        document.querySelectorAll('.reply-rating-btn').forEach(button => {
            button.addEventListener('click', function() {
                const ratingId = this.dataset.ratingId;
                const replyForm = document.getElementById(`reply-form-${ratingId}`);
                const replyText = document.getElementById(`reply-text-${ratingId}`);
                
                // Check if a reply is provided
                if (!replyText.value.trim()) {
                    alert('Please provide a reply');
                    return;
                }
                
                replyForm.submit();
            });
        });
    }
    
    // Toggle rating details
    function setupRatingDetails() {
        document.querySelectorAll('.rating-details-btn').forEach(button => {
            button.addEventListener('click', function() {
                const ratingId = this.dataset.ratingId;
                const detailsRow = document.getElementById(`rating-details-${ratingId}`);
                
                if (detailsRow.style.display === 'none' || !detailsRow.style.display) {
                    detailsRow.style.display = 'table-row';
                    this.textContent = 'Hide Details';
                } else {
                    detailsRow.style.display = 'none';
                    this.textContent = 'Show Details';
                }
            });
        });
    }
    
    // Dashboard statistics chart
    function setupDashboardChart() {
        const statisticsChart = document.getElementById('statistics-chart');
        
        if (statisticsChart) {
            // Get counts from data attributes
            const pendingCount = parseInt(statisticsChart.dataset.pendingCount) || 0;
            const confirmedCount = parseInt(statisticsChart.dataset.confirmedCount) || 0;
            const cancelledCount = parseInt(statisticsChart.dataset.cancelledCount) || 0;
            
            // Create chart
            new Chart(statisticsChart, {
                type: 'pie',
                data: {
                    labels: ['Pending', 'Confirmed', 'Cancelled'],
                    datasets: [{
                        data: [pendingCount, confirmedCount, cancelledCount],
                        backgroundColor: ['#ffc107', '#28a745', '#dc3545']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        },
                        title: {
                            display: true,
                            text: 'Booking Status Distribution'
                        }
                    }
                }
            });
        }
    }
    
    // Ratings chart
    function setupRatingsChart() {
        const ratingsChart = document.getElementById('ratings-chart');
        
        if (ratingsChart) {
            // Get counts from data attributes
            const star1 = parseInt(ratingsChart.dataset.star1) || 0;
            const star2 = parseInt(ratingsChart.dataset.star2) || 0;
            const star3 = parseInt(ratingsChart.dataset.star3) || 0;
            const star4 = parseInt(ratingsChart.dataset.star4) || 0;
            const star5 = parseInt(ratingsChart.dataset.star5) || 0;
            
            // Create chart
            new Chart(ratingsChart, {
                type: 'bar',
                data: {
                    labels: ['1 Star', '2 Stars', '3 Stars', '4 Stars', '5 Stars'],
                    datasets: [{
                        label: 'Number of Ratings',
                        data: [star1, star2, star3, star4, star5],
                        backgroundColor: [
                            '#dc3545',
                            '#fd7e14',
                            '#ffc107',
                            '#20c997',
                            '#28a745'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        title: {
                            display: true,
                            text: 'Rating Distribution'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            precision: 0
                        }
                    }
                }
            });
        }
    }
    
    // Initialize admin dashboard
    function initializeAdminDashboard() {
        setupBookingDetails();
        setupCancelBooking();
        setupConfirmBooking();
        setupRatingReplies();
        setupRatingDetails();
        setupDashboardChart();
        setupRatingsChart();
    }
    
    // Create charts
    setupDashboardChart();
    setupRatingsChart();
    
    // Search functionality for tables
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('keyup', function() {
            const searchText = this.value.toLowerCase();
            const tableRows = document.querySelectorAll('table tbody tr:not(.details-row)');
            
            tableRows.forEach(row => {
                const text = row.textContent.toLowerCase();
                if (text.includes(searchText)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }
    
    // Date range filter
    const startDateFilter = document.getElementById('start-date-filter');
    const endDateFilter = document.getElementById('end-date-filter');
    const applyFilterBtn = document.getElementById('apply-filter');
    
    if (startDateFilter && endDateFilter && applyFilterBtn) {
        applyFilterBtn.addEventListener('click', function() {
            const startDate = startDateFilter.value ? new Date(startDateFilter.value) : null;
            const endDate = endDateFilter.value ? new Date(endDateFilter.value) : null;
            
            if (!startDate && !endDate) {
                return;
            }
            
            const tableRows = document.querySelectorAll('table tbody tr:not(.details-row)');
            
            tableRows.forEach(row => {
                const dateCell = row.querySelector('.booking-date');
                if (dateCell) {
                    const rowDate = new Date(dateCell.dataset.date);
                    
                    let showRow = true;
                    if (startDate && rowDate < startDate) {
                        showRow = false;
                    }
                    if (endDate && rowDate > endDate) {
                        showRow = false;
                    }
                    
                    row.style.display = showRow ? '' : 'none';
                }
            });
        });
    }
});
