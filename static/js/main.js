// Weather Monitoring App - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize animations
    initAnimations();

    // Initialize temperature tooltips
    initTemperatureTooltips();

    // Auto-refresh weather data every 10 minutes
    setInterval(function() {
        // Could implement auto-refresh here if needed
    }, 600000);

    // Handle location search on Enter key
    const searchInput = document.getElementById('locationSearch');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchLocations();
            }
        });

        // Add focus animation
        searchInput.addEventListener('focus', function() {
            this.parentElement.style.transform = 'scale(1.02)';
        });

        searchInput.addEventListener('blur', function() {
            this.parentElement.style.transform = 'scale(1)';
        });
    }

    // Add ripple effect to buttons
    addRippleEffect();

    // Add parallax effect to cards
    addParallaxEffect();
});

function initAnimations() {
    // Stagger animation for location cards
    const cards = document.querySelectorAll('.location-card');
    cards.forEach((card, index) => {
        card.style.animationDelay = `${0.1 + (index * 0.1)}s`;
    });

    // Fade in detail items
    const detailItems = document.querySelectorAll('.detail-item');
    detailItems.forEach((item, index) => {
        item.style.opacity = '0';
        item.style.transform = 'translateX(-20px)';
        setTimeout(() => {
            item.style.transition = 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
            item.style.opacity = '1';
            item.style.transform = 'translateX(0)';
        }, 100 + (index * 50));
    });
}

function addRippleEffect() {
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;

            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.classList.add('ripple');

            this.appendChild(ripple);

            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
}

function addParallaxEffect() {
    const cards = document.querySelectorAll('.location-card, .forecast-day');

    cards.forEach(card => {
        card.addEventListener('mousemove', function(e) {
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const centerX = rect.width / 2;
            const centerY = rect.height / 2;

            const rotateX = (y - centerY) / 20;
            const rotateY = (centerX - x) / 20;

            this.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-8px)`;
        });

        card.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });
    });
}

// Temperature conversion utilities
function celsiusToFahrenheit(celsius) {
    return (celsius * 9/5) + 32;
}

function fahrenheitToCelsius(fahrenheit) {
    return (fahrenheit - 32) * 5/9;
}

function extractTemperature(text) {
    // Only match patterns with explicit temperature symbols (°C or °F or just °)
    // This prevents matching percentages, moon phases, etc.
    const celsiusMatch = text.match(/^([-+]?\d+\.?\d*)\s*°\s*C$/i);
    const fahrenheitMatch = text.match(/^([-+]?\d+\.?\d*)\s*°\s*F$/i);
    const degreeMatch = text.match(/^([-+]?\d+\.?\d*)\s*°$/);

    if (celsiusMatch) {
        return { value: parseFloat(celsiusMatch[1]), unit: 'C' };
    } else if (fahrenheitMatch) {
        return { value: parseFloat(fahrenheitMatch[1]), unit: 'F' };
    } else if (degreeMatch) {
        // Just a degree symbol, assume Celsius
        return { value: parseFloat(degreeMatch[1]), unit: 'C' };
    }
    return null;
}

function initTemperatureTooltips() {
    console.log('🌡️ Initializing temperature tooltips...');

    // Create tooltip container at body level to avoid overflow clipping
    let tooltipContainer = document.getElementById('tooltip-container');
    if (!tooltipContainer) {
        tooltipContainer = document.createElement('div');
        tooltipContainer.id = 'tooltip-container';
        document.body.appendChild(tooltipContainer);
    }

    // Create the tooltip element
    const tooltip = document.createElement('div');
    tooltip.className = 'temperature-tooltip';
    tooltipContainer.appendChild(tooltip);

    // Find all temperature elements
    const tempSelectors = [
        '.temp-value',
        '.temp-large',
        '.forecast-high',
        '.forecast-low',
        '.detail-item .value',
        '.weather-item .value',
        '.forecast-temps .high',
        '.forecast-temps .low',
        '.weekly-avg-value'
    ];

    let tooltipCount = 0;

    tempSelectors.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        elements.forEach(element => {
            const text = element.textContent.trim();
            const temp = extractTemperature(text);

            if (temp) {
                let convertedTemp, tooltipText;

                if (temp.unit === 'C') {
                    convertedTemp = celsiusToFahrenheit(temp.value);
                    tooltipText = `${convertedTemp.toFixed(1)}°F`;
                } else {
                    convertedTemp = fahrenheitToCelsius(temp.value);
                    tooltipText = `${convertedTemp.toFixed(1)}°C`;
                }

                // Add tooltip class and data attribute
                element.classList.add('temp-tooltip');
                element.setAttribute('data-tooltip', tooltipText);
                tooltipCount++;

                console.log(`Added tooltip to ${selector}: ${text} → ${tooltipText}`);

                let scrollListener = null;

                // Show tooltip on hover
                element.addEventListener('mouseenter', function(e) {
                    console.log('🎯 Tooltip hover detected!', tooltipText);
                    this.style.transform = 'scale(1.05)';

                    // Update tooltip position
                    const updatePosition = () => {
                        const rect = this.getBoundingClientRect();
                        const tooltipLeft = rect.left + (rect.width / 2);
                        const tooltipTop = rect.top;

                        tooltip.textContent = tooltipText;
                        tooltip.style.left = `${tooltipLeft}px`;
                        tooltip.style.top = `${tooltipTop}px`;

                        console.log(`✨ Showing tooltip at: left=${tooltipLeft}px, top=${tooltipTop}px`);
                    };

                    // Set initial position and show
                    updatePosition();
                    tooltip.classList.add('visible');

                    // Update position on scroll
                    scrollListener = updatePosition;
                    window.addEventListener('scroll', scrollListener);
                    window.addEventListener('resize', scrollListener);
                });

                element.addEventListener('mouseleave', function() {
                    this.style.transform = 'scale(1)';
                    tooltip.classList.remove('visible');

                    // Remove listeners
                    if (scrollListener) {
                        window.removeEventListener('scroll', scrollListener);
                        window.removeEventListener('resize', scrollListener);
                        scrollListener = null;
                    }
                });
            }
        });
    });

    console.log(`✅ Initialized ${tooltipCount} temperature tooltips`);
}

// Utility function to format dates
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Utility function to format time
function formatTime(timeString) {
    if (!timeString) return '';
    const [hours, minutes] = timeString.split(':');
    const date = new Date();
    date.setHours(parseInt(hours), parseInt(minutes));
    return date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });
}
