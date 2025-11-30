document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const roomSelect = document.getElementById('room-select');
    const checkInDate = document.getElementById('check-in-date');
    const checkOutDate = document.getElementById('check-out-date');
    const guestsInput = document.getElementById('guests');
    const roomDetails = document.getElementById('room-details');
    const priceDisplay = document.getElementById('price-display');
    const amenitiesContainer = document.getElementById('amenities-container');
    const bookingForm = document.getElementById('booking-form');
    
    // Set min date to today for check-in
    if (checkInDate) {
        const today = new Date();
        const todayStr = today.toISOString().split('T')[0];
        checkInDate.min = todayStr;
        
        // Set default check-in to today and check-out to tomorrow
        checkInDate.value = todayStr;
        
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        const tomorrowStr = tomorrow.toISOString().split('T')[0];
        checkOutDate.min = tomorrowStr;
        checkOutDate.value = tomorrowStr;
    }
    
    // Load rooms data
    function loadRooms() {
        if (!roomSelect) return;
        
        fetch('/api/rooms')
            .then(response => response.json())
            .then(rooms => {
                roomSelect.innerHTML = '';
                rooms.forEach(room => {
                    const option = document.createElement('option');
                    option.value = room.id;
                    option.textContent = `${room.name} (Max ${room.capacity} guests) - ₱${room.price_per_night}/night`;
                    option.dataset.capacity = room.capacity;
                    option.dataset.price = room.price_per_night;
                    option.dataset.image = room.image_url;
                    option.dataset.description = room.description;
                    roomSelect.appendChild(option);
                });
            })
            .catch(error => console.error('Error loading rooms:', error));
    }
    
    // Load amenities
    function loadAmenities() {
        if (!amenitiesContainer) return;
        
        fetch('/api/amenities')
            .then(response => response.json())
            .then(amenities => {
                amenitiesContainer.innerHTML = '<h4 class="mt-4">Amenities</h4>';
                amenities.forEach(amenity => {
                    const amenityDiv = document.createElement('div');
                    amenityDiv.className = 'row mb-3 amenity-item';
                    amenityDiv.innerHTML = `
                        <div class="col-md-6">
                            <label class="form-label">${amenity.name} (₱${amenity.price})</label>
                            <small class="text-muted d-block">${amenity.description}</small>
                        </div>
                        <div class="col-md-6">
                            <div class="input-group">
                                <button type="button" class="btn btn-outline-secondary decrement" data-amenity-id="${amenity.id}">-</button>
                                <input type="number" name="amenity_${amenity.id}" class="form-control text-center amenity-quantity" value="0" min="0" data-price="${amenity.price}" data-amenity-id="${amenity.id}">
                                <button type="button" class="btn btn-outline-secondary increment" data-amenity-id="${amenity.id}">+</button>
                            </div>
                        </div>
                    `;
                    amenitiesContainer.appendChild(amenityDiv);
                });
                
                // Add event listeners for increment/decrement buttons
                document.querySelectorAll('.increment').forEach(button => {
                    button.addEventListener('click', function() {
                        const amenityId = this.dataset.amenityId;
                        const input = document.querySelector(`input[name="amenity_${amenityId}"]`);
                        input.value = parseInt(input.value) + 1;
                        input.dispatchEvent(new Event('change'));
                    });
                });
                
                document.querySelectorAll('.decrement').forEach(button => {
                    button.addEventListener('click', function() {
                        const amenityId = this.dataset.amenityId;
                        const input = document.querySelector(`input[name="amenity_${amenityId}"]`);
                        if (parseInt(input.value) > 0) {
                            input.value = parseInt(input.value) - 1;
                            input.dispatchEvent(new Event('change'));
                        }
                    });
                });
                
                // Add event listeners for amenity quantity change
                document.querySelectorAll('.amenity-quantity').forEach(input => {
                    input.addEventListener('change', calculateTotalPrice);
                });
            })
            .catch(error => console.error('Error loading amenities:', error));
    }
    
    // Update room details when a room is selected
    function updateRoomDetails() {
        if (!roomSelect || !roomDetails) return;
        
        const selectedOption = roomSelect.options[roomSelect.selectedIndex];
        if (selectedOption.value) {
            const capacity = selectedOption.dataset.capacity;
            const price = selectedOption.dataset.price;
            const image = selectedOption.dataset.image;
            const description = selectedOption.dataset.description;
            
            roomDetails.innerHTML = `
                <div class="card mt-3">
                    <img src="${image}" class="card-img-top" alt="${selectedOption.textContent}" 
                         onerror="this.onerror=null; this.src='/static/images/rooms/' + this.src.split('/').pop(); console.log('Fallback to: ' + this.src);">
                    <div class="card-body">
                        <h5 class="card-title">${selectedOption.textContent.split(' (')[0]}</h5>
                        <p class="card-text">${description}</p>
                        <p class="card-text"><strong>Price:</strong> ₱${price} per night</p>
                        <p class="card-text"><strong>Maximum Guests:</strong> ${capacity}</p>
                    </div>
                </div>
            `;
            
            // Update max guests in input
            if (guestsInput) {
                guestsInput.max = capacity;
                if (parseInt(guestsInput.value) > parseInt(capacity)) {
                    guestsInput.value = capacity;
                }
            }
            
            // Check availability
            checkAvailability();
        } else {
            roomDetails.innerHTML = '<p class="alert alert-info">Please select a room to see details</p>';
        }
    }
    
    // Check room availability for selected dates
    function checkAvailability() {
        if (!roomSelect || !checkInDate || !checkOutDate) return;
        
        const roomId = roomSelect.value;
        const checkIn = checkInDate.value;
        const checkOut = checkOutDate.value;
        
        if (roomId && checkIn && checkOut) {
            fetch(`/api/check_availability?room_id=${roomId}&check_in=${checkIn}&check_out=${checkOut}`)
                .then(response => response.json())
                .then(data => {
                    const availabilityAlert = document.getElementById('availability-alert');
                    if (availabilityAlert) {
                        if (data.available) {
                            availabilityAlert.className = 'alert alert-success';
                            availabilityAlert.textContent = 'Room is available for the selected dates!';
                            document.getElementById('submit-booking').disabled = false;
                        } else {
                            availabilityAlert.className = 'alert alert-danger';
                            availabilityAlert.textContent = data.message;
                            document.getElementById('submit-booking').disabled = true;
                        }
                    }
                })
                .catch(error => console.error('Error checking availability:', error));
                
            // Calculate price
            calculateTotalPrice();
        }
    }
    
    // Calculate total price based on room, dates, and amenities
    function calculateTotalPrice() {
        if (!roomSelect || !checkInDate || !checkOutDate || !priceDisplay) return;
        
        const roomId = roomSelect.value;
        const checkIn = checkInDate.value;
        const checkOut = checkOutDate.value;
        
        if (roomId && checkIn && checkOut) {
            // Collect amenities data
            const amenities = [];
            document.querySelectorAll('.amenity-quantity').forEach(input => {
                const quantity = parseInt(input.value);
                if (quantity > 0) {
                    amenities.push({
                        id: input.dataset.amenityId,
                        quantity: quantity
                    });
                }
            });
            
            fetch(`/api/calculate_price?room_id=${roomId}&check_in=${checkIn}&check_out=${checkOut}&amenities=${JSON.stringify(amenities)}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        priceDisplay.innerHTML = `
                            <div class="card mt-3">
                                <div class="card-header bg-primary text-white">
                                    <h5 class="mb-0">Price Summary</h5>
                                </div>
                                <div class="card-body">
                                    <p><strong>Room Cost:</strong> ₱${data.room_cost.toFixed(2)} (₱${(data.room_cost / data.days).toFixed(2)} x ${data.days} nights)</p>
                                    <p><strong>Amenities Cost:</strong> ₱${data.amenities_cost.toFixed(2)}</p>
                                    <h4 class="mt-3 text-primary">Total: ₱${data.total_cost.toFixed(2)}</h4>
                                </div>
                            </div>
                        `;
                    } else {
                        priceDisplay.innerHTML = `<p class="alert alert-danger">${data.message}</p>`;
                    }
                })
                .catch(error => {
                    console.error('Error calculating price:', error);
                    priceDisplay.innerHTML = '<p class="alert alert-danger">Error calculating price. Please try again.</p>';
                });
        } else {
            priceDisplay.innerHTML = '';
        }
    }
    
    // Initialize booking page
    if (bookingForm) {
        loadRooms();
        loadAmenities();
        
        // Event listeners
        if (roomSelect) {
            roomSelect.addEventListener('change', updateRoomDetails);
        }
        
        if (checkInDate) {
            checkInDate.addEventListener('change', checkAvailability);
        }
        
        if (checkOutDate) {
            checkOutDate.addEventListener('change', checkAvailability);
        }
        
        // Form validation
        bookingForm.addEventListener('submit', function(event) {
            const roomId = roomSelect.value;
            const checkIn = checkInDate.value;
            const checkOut = checkOutDate.value;
            const guests = guestsInput.value;
            
            if (!roomId || !checkIn || !checkOut || !guests) {
                event.preventDefault();
                alert('Please fill all required fields');
            }
            
            // Check if check-out is after check-in
            if (new Date(checkOut) <= new Date(checkIn)) {
                event.preventDefault();
                alert('Check-out date must be after check-in date');
            }
            
            // Check if guests is valid
            const selectedOption = roomSelect.options[roomSelect.selectedIndex];
            if (selectedOption.value) {
                const capacity = parseInt(selectedOption.dataset.capacity);
                if (parseInt(guests) > capacity) {
                    event.preventDefault();
                    alert(`Maximum capacity for this room is ${capacity} guests`);
                }
            }
        });
    }
});
