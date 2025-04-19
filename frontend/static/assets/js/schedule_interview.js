document.addEventListener('DOMContentLoaded', function() {
    // Initialize variables
    let currentDate = new Date();
    let meetings = [];
    
    // DOM elements
    const meetingForm = document.getElementById('meeting-form');
    const calendarDays = document.getElementById('calendar-days');
    const currentMonthElement = document.getElementById('current-month');
    const prevMonthButton = document.getElementById('prev-month');
    const nextMonthButton = document.getElementById('next-month');
    const meetingsContainer = document.getElementById('meetings-container');
    const meetingModal = document.getElementById('meeting-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalContent = document.getElementById('modal-content');
    const closeModal = document.querySelector('.close-modal');
    
    // Initialize the calendar
    updateCalendar();
    
    // Fetch existing meetings from the server
    fetchMeetings();
    
    // Event listeners
    prevMonthButton.addEventListener('click', () => changeMonth(-1));
    nextMonthButton.addEventListener('click', () => changeMonth(1));
    closeModal.addEventListener('click', () => meetingModal.style.display = 'none');
    
    window.addEventListener('click', function(event) {
        if (event.target === meetingModal) {
            meetingModal.style.display = 'none';
        }
    });
    
    // Functions
    function updateCalendar() {
        // Update the month display
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 
                           'July', 'August', 'September', 'October', 'November', 'December'];
        currentMonthElement.textContent = `${monthNames[currentDate.getMonth()]} ${currentDate.getFullYear()}`;
        
        // Clear the calendar
        calendarDays.innerHTML = '';
        
        // Get the first day of the month
        const firstDay = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
        const lastDay = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);
        
        // Get the day of the week for the first day (0 = Sunday, 6 = Saturday)
        const firstDayIndex = firstDay.getDay();
        
        // Get the number of days in the month
        const daysInMonth = lastDay.getDate();
        
        // Get the number of days in the previous month
        const prevLastDay = new Date(currentDate.getFullYear(), currentDate.getMonth(), 0);
        const prevDaysInMonth = prevLastDay.getDate();
        
        // Calculate the number of days to display from the previous month
        const prevDays = firstDayIndex;
        
        // Calculate the number of days to display from the next month
        const nextDays = 42 - (prevDays + daysInMonth); // 42 = 6 rows of 7 days
        
        // Create calendar days
        
        // Previous month days
        for (let i = prevDays - 1; i >= 0; i--) {
            const dayElement = createDayElement(prevDaysInMonth - i, 'other-month');
            calendarDays.appendChild(dayElement);
        }
        
        // Current month days
        const today = new Date();
        for (let i = 1; i <= daysInMonth; i++) {
            const isToday = i === today.getDate() && 
                           currentDate.getMonth() === today.getMonth() && 
                           currentDate.getFullYear() === today.getFullYear();
            
            const dayElement = createDayElement(i, isToday ? 'today' : '');
            
            // Add meeting indicators
            const meetingDate = new Date(currentDate.getFullYear(), currentDate.getMonth(), i);
            const dayMeetings = getMeetingsForDate(meetingDate);
            
            if (dayMeetings.length > 0) {
                const meetingsDiv = document.createElement('div');
                meetingsDiv.className = 'day-meetings';
                
                dayMeetings.forEach(meeting => {
                    const meetingItem = document.createElement('div');
                    meetingItem.className = 'meeting-item';
                    meetingItem.textContent = meeting.title;
                    meetingItem.dataset.meetingId = meeting.id;
                    meetingItem.addEventListener('click', () => showMeetingDetails(meeting));
                    meetingsDiv.appendChild(meetingItem);
                });
                
                dayElement.appendChild(meetingsDiv);
            }
            
            calendarDays.appendChild(dayElement);
        }
        
        // Next month days
        for (let i = 1; i <= nextDays; i++) {
            const dayElement = createDayElement(i, 'other-month');
            calendarDays.appendChild(dayElement);
        }
        
        // Update the meeting list
        updateMeetingList();
    }
    
    function createDayElement(day, className) {
        const dayElement = document.createElement('div');
        dayElement.className = `calendar-day ${className}`;
        
        const dayNumber = document.createElement('div');
        dayNumber.className = 'day-number';
        dayNumber.textContent = day;
        
        dayElement.appendChild(dayNumber);
        return dayElement;
    }
    
    function changeMonth(delta) {
        currentDate.setMonth(currentDate.getMonth() + delta);
        updateCalendar();
    }
    
    function fetchMeetings() {
        // In a real application, this would be an API call to your Flask backend
        // For demonstration purposes, we'll use sample data
        fetch('/api/meetings')
            .then(response => response.json())
            .then(data => {
                meetings = data;
                updateCalendar();
                updateMeetingList();
            })
            .catch(error => {
                console.error('Error fetching meetings:', error);
                // Use sample data for demonstration
                meetings = getSampleMeetings();
                updateCalendar();
                updateMeetingList();
            });
    }
    
    function getSampleMeetings() {
        const today = new Date();
        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);
        
        return [
            {
                id: 1,
                title: 'Team Standup',
                date: formatDate(today),
                start_time: '09:00',
                end_time: '09:30',
                attendees: 'john@example.com, sarah@example.com',
                description: 'Daily team standup meeting to discuss progress and blockers.'
            },
            {
                id: 2,
                title: 'Project Review',
                date: formatDate(today),
                start_time: '14:00',
                end_time: '15:00',
                attendees: 'manager@example.com, team@example.com',
                description: 'Review project milestones and deliverables.'
            },
            {
                id: 3,
                title: 'Client Meeting',
                date: formatDate(tomorrow),
                start_time: '11:00',
                end_time: '12:00',
                attendees: 'client@example.com, sales@example.com',
                description: 'Discuss project requirements with the client.'
            }
        ];
    }
    
    function formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }
    
    function getMeetingsForDate(date) {
        const dateString = formatDate(date);
        return meetings.filter(meeting => meeting.date === dateString);
    }
    
    function updateMeetingList() {
        meetingsContainer.innerHTML = '';
        
        // Sort meetings by date and time
        const sortedMeetings = [...meetings].sort((a, b) => {
            if (a.date !== b.date) {
                return new Date(a.date) - new Date(b.date);
            }
            return a.start_time.localeCompare(b.start_time);
        });
        
        // Filter to show only upcoming meetings
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        
        const upcomingMeetings = sortedMeetings.filter(meeting => {
            const meetingDate = new Date(meeting.date);
            return meetingDate >= today;
        });
        
        if (upcomingMeetings.length === 0) {
            const noMeetings = document.createElement('p');
            noMeetings.textContent = 'No upcoming meetings scheduled.';
            meetingsContainer.appendChild(noMeetings);
            return;
        }
        
        upcomingMeetings.forEach(meeting => {
            const meetingCard = document.createElement('div');
            meetingCard.className = 'meeting-card';
            meetingCard.dataset.meetingId = meeting.id;
            
            const title = document.createElement('h4');
            title.textContent = meeting.title;
            
            const time = document.createElement('p');
            time.className = 'meeting-time';
            
            // Format the date
            const meetingDate = new Date(meeting.date);
            const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
            const formattedDate = meetingDate.toLocaleDateString('en-US', options);
            
            time.textContent = `${formattedDate}, ${meeting.start_time} - ${meeting.end_time}`;
            
            const attendees = document.createElement('p');
            attendees.className = 'meeting-attendees';
            attendees.textContent = `Attendees: ${meeting.attendees || 'None'}`;
            
            meetingCard.appendChild(title);
            meetingCard.appendChild(time);
            meetingCard.appendChild(attendees);
            
            meetingCard.addEventListener('click', () => showMeetingDetails(meeting));
            
            meetingsContainer.appendChild(meetingCard);
        });
    }
    
    function showMeetingDetails(meeting) {
        modalTitle.textContent = meeting.title;
        
        // Format the date
        const meetingDate = new Date(meeting.date);
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        const formattedDate = meetingDate.toLocaleDateString('en-US', options);
        
        modalContent.innerHTML = `
            <p><strong>Date:</strong> ${formattedDate}</p>
            <p><strong>Time:</strong> ${meeting.start_time} - ${meeting.end_time}</p>
            <p><strong>Attendees:</strong> ${meeting.attendees || 'None'}</p>
            <p><strong>Description:</strong> ${meeting.description || 'No description provided.'}</p>
            <div class="modal-actions">
                <button class="btn-secondary" onclick="editMeeting(${meeting.id})">Edit</button>
                <button class="btn-secondary" onclick="deleteMeeting(${meeting.id})">Delete</button>
            </div>
        `;
        
        meetingModal.style.display = 'block';
    }
    
    function handleFormSubmit(event) {
        event.preventDefault();
        
        // Get form data
        const formData = new FormData(meetingForm);
        const meetingData = {
            id: meetings.length + 1, // In a real app, this would be generated by the server
            title: formData.get('title'),
            date: formData.get('date'),
            start_time: formData.get('start_time'),
            end_time: formData.get('end_time'),
            attendees: formData.get('attendees'),
            description: formData.get('description')
        };
        
        // Validate form data
        if (!validateMeetingData(meetingData)) {
            return;
        }
        
        // In a real application, this would be an API call to your Flask backend
        // For demonstration purposes, we'll just add it to our local array
        saveMeeting(meetingData);
    }
    
    function validateMeetingData(meetingData) {
        // Check if end time is after start time
        if (meetingData.start_time >= meetingData.end_time) {
            alert('End time must be after start time.');
            return false;
        }
        
        // Check for conflicts with existing meetings
        const conflicts = meetings.filter(meeting => {
            if (meeting.date !== meetingData.date) {
                return false;
            }
            
            const newStart = meetingData.start_time;
            const newEnd = meetingData.end_time;
            const existingStart = meeting.start_time;
            const existingEnd = meeting.end_time;
            
            // Check if the new meeting overlaps with an existing meeting
            return (newStart < existingEnd && newEnd > existingStart);
        });
        
        if (conflicts.length > 0) {
            alert('This meeting conflicts with an existing meeting. Please choose a different time.');
            return false;
        }
        
        return true;
    }
    
    function saveMeeting(meetingData) {
        // In a real application, this would be an API call to your Flask backend
        fetch('/api/meetings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(meetingData),
        })
        .then(response => response.json())
        .then(data => {
            // Add the new meeting to our local array
            meetings.push(data);
            
            // Update the calendar and meeting list
            updateCalendar();
            updateMeetingList();
            
            // Reset the form
            meetingForm.reset();
            
            // Show success message
            alert('Meeting scheduled successfully!');
        })
        .catch(error => {
            console.error('Error saving meeting:', error);
            
            // For demonstration purposes, we'll just add it to our local array
            meetings.push(meetingData);
            updateCalendar();
            updateMeetingList();
            meetingForm.reset();
            alert('Meeting scheduled successfully!');
        });
    }
    
    // These functions would be implemented in a real application
    window.editMeeting = function(meetingId) {
        const meeting = meetings.find(m => m.id === meetingId);
        if (!meeting) return;
        
        // Populate the form with meeting data
        document.getElementById('title').value = meeting.title;
        document.getElementById('date').value = meeting.date;
        document.getElementById('start-time').value = meeting.start_time;
        document.getElementById('end-time').value = meeting.end_time;
        document.getElementById('attendees').value = meeting.attendees || '';
        document.getElementById('description').value = meeting.description || '';
        
        // Scroll to the form
        document.getElementById('schedule').scrollIntoView({ behavior: 'smooth' });
        
        // Close the modal
        meetingModal.style.display = 'none';
    };
    
    window.deleteMeeting = function(meetingId) {
        if (!confirm('Are you sure you want to delete this meeting?')) {
            return;
        }
        
        // In a real application, this would be an API call to your Flask backend
        fetch(`/api/meetings/${meetingId}`, {
            method: 'DELETE',
        })
        .then(response => {
            if (response.ok) {
                // Remove the meeting from our local array
                meetings = meetings.filter(m => m.id !== meetingId);
                
                // Update the calendar and meeting list
                updateCalendar();
                updateMeetingList();
                
                // Close the modal
                meetingModal.style.display = 'none';
                
                // Show success message
                alert('Meeting deleted successfully!');
            }
        })
        .catch(error => {
            console.error('Error deleting meeting:', error);
            
            // For demonstration purposes, we'll just remove it from our local array
            meetings = meetings.filter(m => m.id !== meetingId);
            updateCalendar();
            updateMeetingList();
            meetingModal.style.display = 'none';
            alert('Meeting deleted successfully!');
        });
    };
});