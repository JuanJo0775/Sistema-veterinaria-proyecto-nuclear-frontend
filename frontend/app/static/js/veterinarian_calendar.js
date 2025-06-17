// frontend/app/static/js/veterinarian_calendar.js

class VeterinarianCalendar {
    constructor() {
        this.currentDate = new Date();
        this.currentView = 'month'; // month, week, day
        this.appointments = [];
        this.selectedDate = null;
        this.monthNames = [
            'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
        ];
        this.dayNames = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
        this.init();
    }

    init() {
        console.log('🔧 Inicializando calendario del veterinario...');
        this.setupEventListeners();
        this.loadCalendarData();
        this.renderCalendar();
    }

    setupEventListeners() {
        // Navegación del calendario
        document.addEventListener('click', (e) => {
            if (e.target.matches('.nav-btn[data-action="prev"]')) {
                this.navigateCalendar(-1);
            } else if (e.target.matches('.nav-btn[data-action="next"]')) {
                this.navigateCalendar(1);
            }
        });

        // Botones de vista
        document.addEventListener('click', (e) => {
            if (e.target.matches('.view-btn')) {
                const view = e.target.dataset.view;
                this.changeView(view);
            }
        });

        // Funciones globales
        window.navigateCalendar = (direction) => this.navigateCalendar(direction);
        window.changeView = (view) => this.changeView(view);
        window.selectDate = (date) => this.selectDate(date);
        window.viewAppointmentDetails = (appointmentId) => this.viewAppointmentDetails(appointmentId);
    }

    async loadCalendarData() {
        try {
            this.showLoading();
            console.log('📅 Cargando datos del calendario...');

            const month = this.currentDate.getMonth() + 1;
            const year = this.currentDate.getFullYear();

            const response = await fetch(`/api/veterinarian/calendar-data?month=${month}&year=${year}`);
            const data = await response.json();

            if (data.success) {
                this.appointments = data.appointments || [];
                this.renderCalendar();
                console.log('✅ Datos del calendario cargados exitosamente');
            } else {
                throw new Error(data.message || 'Error obteniendo datos del calendario');
            }

        } catch (error) {
            console.error('❌ Error cargando calendario:', error);
            this.showError('Error cargando los datos del calendario');
            this.appointments = [];
            this.renderCalendar();
        } finally {
            this.hideLoading();
        }
    }

    renderCalendar() {
        this.updateCalendarHeader();

        switch (this.currentView) {
            case 'month':
                this.renderMonthView();
                break;
            case 'week':
                this.renderWeekView();
                break;
            case 'day':
                this.renderDayView();
                break;
        }

        this.updateViewButtons();
    }

    updateCalendarHeader() {
        const titleElement = document.querySelector('.month-year');
        const prevBtn = document.querySelector('.nav-btn[data-action="prev"]');
        const nextBtn = document.querySelector('.nav-btn[data-action="next"]');

        if (titleElement) {
            let title = '';
            switch (this.currentView) {
                case 'month':
                    title = `${this.monthNames[this.currentDate.getMonth()]} ${this.currentDate.getFullYear()}`;
                    break;
                case 'week':
                    const weekStart = this.getWeekStart(this.currentDate);
                    const weekEnd = this.getWeekEnd(this.currentDate);
                    title = `${weekStart.getDate()} - ${weekEnd.getDate()} ${this.monthNames[this.currentDate.getMonth()]} ${this.currentDate.getFullYear()}`;
                    break;
                case 'day':
                    title = `${this.currentDate.getDate()} ${this.monthNames[this.currentDate.getMonth()]} ${this.currentDate.getFullYear()}`;
                    break;
            }
            titleElement.textContent = title;
        }

        // Configurar botones de navegación
        if (prevBtn && nextBtn) {
            prevBtn.innerHTML = '❮';
            nextBtn.innerHTML = '❯';
        }
    }

    renderMonthView() {
        const container = document.querySelector('.calendar-grid');
        if (!container) return;

        // Configurar grid para vista mensual
        container.style.gridTemplateColumns = 'repeat(7, 1fr)';
        container.innerHTML = '';

        // Agregar encabezados de días
        this.dayNames.forEach(dayName => {
            const dayHeader = document.createElement('div');
            dayHeader.className = 'calendar-day-header';
            dayHeader.textContent = dayName;
            container.appendChild(dayHeader);
        });

        // Obtener primer día del mes y número de días
        const firstDay = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth(), 1);
        const lastDay = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth() + 1, 0);
        const startDate = new Date(firstDay);
        startDate.setDate(startDate.getDate() - firstDay.getDay());

        // Generar 42 días (6 semanas)
        for (let i = 0; i < 42; i++) {
            const currentDate = new Date(startDate);
            currentDate.setDate(startDate.getDate() + i);

            const dayElement = this.createDayElement(currentDate);
            container.appendChild(dayElement);
        }
    }

    createDayElement(date) {
        const div = document.createElement('div');
        const isCurrentMonth = date.getMonth() === this.currentDate.getMonth();
        const isToday = this.isToday(date);
        const isSelected = this.isSelected(date);

        div.className = `calendar-day ${isCurrentMonth ? 'current-month' : 'other-month'} ${isToday ? 'today' : ''} ${isSelected ? 'selected' : ''}`;
        div.onclick = () => this.selectDate(date);

        const dayAppointments = this.getAppointmentsForDate(date);

        div.innerHTML = `
            <div class="day-number">${date.getDate()}</div>
            <div class="day-appointments">
                ${dayAppointments.slice(0, 3).map(apt => this.createAppointmentPreview(apt)).join('')}
                ${dayAppointments.length > 3 ? `<div class="more-appointments">+${dayAppointments.length - 3} más</div>` : ''}
            </div>
        `;

        return div;
    }

    createAppointmentPreview(appointment) {
        const typeClass = this.getAppointmentTypeClass(appointment.appointment_type);
        return `
            <div class="appointment-preview ${typeClass}" onclick="event.stopPropagation(); viewAppointmentDetails('${appointment.id}')" title="${appointment.pet_name} - ${appointment.appointment_time}">
                <span class="apt-time">${appointment.appointment_time}</span>
                <span class="apt-pet">${appointment.pet_name || 'Sin nombre'}</span>
            </div>
        `;
    }

    renderWeekView() {
        const container = document.querySelector('.calendar-grid');
        if (!container) return;

        container.style.gridTemplateColumns = '80px repeat(7, 1fr)';
        container.innerHTML = '';

        // Header con días de la semana
        const timeHeader = document.createElement('div');
        timeHeader.className = 'time-header';
        timeHeader.textContent = 'Hora';
        container.appendChild(timeHeader);

        const weekStart = this.getWeekStart(this.currentDate);
        for (let i = 0; i < 7; i++) {
            const day = new Date(weekStart);
            day.setDate(weekStart.getDate() + i);

            const dayHeader = document.createElement('div');
            dayHeader.className = `week-day-header ${this.isToday(day) ? 'today' : ''}`;
            dayHeader.innerHTML = `
                <div class="day-name">${this.dayNames[day.getDay()]}</div>
                <div class="day-date">${day.getDate()}</div>
            `;
            container.appendChild(dayHeader);
        }

        // Generar franjas horarias (8 AM - 8 PM)
        for (let hour = 8; hour <= 20; hour++) {
            // Columna de hora
            const timeSlot = document.createElement('div');
            timeSlot.className = 'time-slot';
            timeSlot.textContent = `${hour}:00`;
            container.appendChild(timeSlot);

            // Columnas de días
            for (let i = 0; i < 7; i++) {
                const day = new Date(weekStart);
                day.setDate(weekStart.getDate() + i);

                const hourSlot = document.createElement('div');
                hourSlot.className = 'hour-slot';
                hourSlot.dataset.date = day.toISOString().split('T')[0];
                hourSlot.dataset.hour = hour;

                // Agregar citas para esta hora y día
                const hourAppointments = this.getAppointmentsForHour(day, hour);
                hourAppointments.forEach(apt => {
                    const aptElement = this.createWeekAppointmentElement(apt);
                    hourSlot.appendChild(aptElement);
                });

                container.appendChild(hourSlot);
            }
        }
    }

    createWeekAppointmentElement(appointment) {
        const div = document.createElement('div');
        div.className = `week-appointment ${this.getAppointmentTypeClass(appointment.appointment_type)}`;
        div.onclick = () => this.viewAppointmentDetails(appointment.id);

        div.innerHTML = `
            <div class="apt-time">${appointment.appointment_time}</div>
            <div class="apt-details">
                <div class="apt-pet">${appointment.pet_name || 'Sin nombre'}</div>
                <div class="apt-owner">${appointment.owner_name || ''}</div>
            </div>
        `;

        return div;
    }

    renderDayView() {
        const container = document.querySelector('.calendar-grid');
        if (!container) return;

        container.style.gridTemplateColumns = '80px 1fr';
        container.innerHTML = '';

        const dayAppointments = this.getAppointmentsForDate(this.currentDate);

        // Header del día
        const dayHeader = document.createElement('div');
        dayHeader.className = 'day-view-header';
        dayHeader.style.gridColumn = '1 / -1';
        dayHeader.innerHTML = `
            <div class="day-title">
                <h3>${this.dayNames[this.currentDate.getDay()]} ${this.currentDate.getDate()}</h3>
                <div class="day-subtitle">${dayAppointments.length} citas programadas</div>
            </div>
        `;
        container.appendChild(dayHeader);

        // Franjas horarias (8 AM - 8 PM)
        for (let hour = 8; hour <= 20; hour++) {
            // Columna de hora
            const timeSlot = document.createElement('div');
            timeSlot.className = 'time-slot';
            timeSlot.textContent = `${hour}:00`;
            container.appendChild(timeSlot);

            // Slot del día
            const hourSlot = document.createElement('div');
            hourSlot.className = 'day-hour-slot';
            hourSlot.dataset.hour = hour;

            // Agregar citas para esta hora
            const hourAppointments = this.getAppointmentsForHour(this.currentDate, hour);
            hourAppointments.forEach(apt => {
                const aptElement = this.createDayAppointmentElement(apt);
                hourSlot.appendChild(aptElement);
            });

            // Si no hay citas, mostrar slot vacío clickeable
            if (hourAppointments.length === 0) {
                hourSlot.classList.add('empty-slot');
                hourSlot.onclick = () => this.createNewAppointment(this.currentDate, hour);
                hourSlot.innerHTML = '<div class="add-appointment">+ Agregar cita</div>';
            }

            container.appendChild(hourSlot);
        }
    }

    createDayAppointmentElement(appointment) {
        const div = document.createElement('div');
        div.className = `day-appointment ${this.getAppointmentTypeClass(appointment.appointment_type)} ${this.getStatusClass(appointment.status)}`;
        div.onclick = () => this.viewAppointmentDetails(appointment.id);

        div.innerHTML = `
            <div class="apt-header">
                <span class="apt-time">${appointment.appointment_time}</span>
                <span class="apt-status">${this.getStatusText(appointment.status)}</span>
            </div>
            <div class="apt-patient">
                <strong>${appointment.pet_name || 'Sin nombre'}</strong>
                <span class="species">${appointment.pet_species || ''}</span>
            </div>
            <div class="apt-owner">Propietario: ${appointment.owner_name || 'No especificado'}</div>
            <div class="apt-reason">${appointment.reason || 'Consulta general'}</div>
            <div class="apt-actions">
                <button class="btn-action small" onclick="event.stopPropagation(); editAppointment('${appointment.id}')" title="Editar">✏️</button>
                <button class="btn-action small" onclick="event.stopPropagation(); startConsultation('${appointment.id}')" title="Iniciar consulta">🩺</button>
            </div>
        `;

        return div;
    }

    // Utilidades de fecha
    getWeekStart(date) {
        const start = new Date(date);
        start.setDate(date.getDate() - date.getDay());
        return start;
    }

    getWeekEnd(date) {
        const end = new Date(date);
        end.setDate(date.getDate() + (6 - date.getDay()));
        return end;
    }

    isToday(date) {
        const today = new Date();
        return date.toDateString() === today.toDateString();
    }

    isSelected(date) {
        return this.selectedDate && date.toDateString() === this.selectedDate.toDateString();
    }

    // Filtros de citas
    getAppointmentsForDate(date) {
        const dateString = date.toISOString().split('T')[0];
        return this.appointments.filter(apt =>
            apt.appointment_date === dateString
        );
    }

    getAppointmentsForHour(date, hour) {
        const dayAppointments = this.getAppointmentsForDate(date);
        return dayAppointments.filter(apt => {
            const aptHour = parseInt(apt.appointment_time.split(':')[0]);
            return aptHour === hour;
        });
    }

    // Navegación
    navigateCalendar(direction) {
        switch (this.currentView) {
            case 'month':
                this.currentDate.setMonth(this.currentDate.getMonth() + direction);
                break;
            case 'week':
                this.currentDate.setDate(this.currentDate.getDate() + (direction * 7));
                break;
            case 'day':
                this.currentDate.setDate(this.currentDate.getDate() + direction);
                break;
        }
        this.loadCalendarData();
    }

    changeView(view) {
        this.currentView = view;
        this.renderCalendar();
    }

    updateViewButtons() {
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.view === this.currentView) {
                btn.classList.add('active');
            }
        });
    }

    selectDate(date) {
        this.selectedDate = new Date(date);
        this.currentDate = new Date(date);
        this.renderCalendar();
    }

    // Acciones de citas
    viewAppointmentDetails(appointmentId) {
        window.location.href = `/veterinarian/appointments/${appointmentId}`;
    }

    createNewAppointment(date, hour) {
        const dateString = date.toISOString().split('T')[0];
        const timeString = `${hour.toString().padStart(2, '0')}:00`;
        window.location.href = `/veterinarian/appointments/new?date=${dateString}&time=${timeString}`;
    }

    // Clasificaciones de citas
    getAppointmentTypeClass(type) {
        const typeClasses = {
            'consultation': 'consultation',
            'surgery': 'surgery',
            'vaccination': 'vaccination',
            'emergency': 'emergency',
            'control': 'control'
        };
        return typeClasses[type] || 'consultation';
    }

    getStatusClass(status) {
        const statusClasses = {
            'scheduled': 'scheduled',
            'confirmed': 'confirmed',
            'in_progress': 'in-progress',
            'completed': 'completed',
            'cancelled': 'cancelled',
            'no_show': 'no-show'
        };
        return statusClasses[status] || 'scheduled';
    }

    getStatusText(status) {
        const statusTexts = {
            'scheduled': 'Programada',
            'confirmed': 'Confirmada',
            'in_progress': 'En Progreso',
            'completed': 'Completada',
            'cancelled': 'Cancelada',
            'no_show': 'No Asistió'
        };
        return statusTexts[status] || 'Programada';
    }

    // Estados de carga
    showLoading() {
        const calendarGrid = document.querySelector('.calendar-grid');
        if (calendarGrid) {
            calendarGrid.innerHTML = `
                <div class="calendar-loading">
                    <div class="spinner"></div>
                    <div>Cargando calendario...</div>
                </div>
            `;
        }
    }

    hideLoading() {
        // El loading se oculta al renderizar el calendario
    }

    showError(message) {
        this.showToast(message, 'error');
    }

    showToast(message, type) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;

        const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️';

        toast.innerHTML = `
            <div class="toast-content">
                <span class="toast-icon">${icon}</span>
                <span class="toast-message">${message}</span>
            </div>
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 5000);
    }
}

// Funciones globales para botones
window.editAppointment = function(appointmentId) {
    window.location.href = `/veterinarian/appointments/${appointmentId}/edit`;
};

window.startConsultation = function(appointmentId) {
    window.location.href = `/veterinarian/medical-records/new?appointment_id=${appointmentId}`;
};

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    window.veterinarianCalendar = new VeterinarianCalendar();
});

// CSS adicional para el calendario
const calendarStyles = `
<style>
.calendar-grid {
    display: grid;
    gap: 1px;
    background: #B7E4C7;
    border: 1px solid #B7E4C7;
}

.calendar-day-header {
    background: #2D6A4F;
    color: white;
    padding: 15px 10px;
    text-align: center;
    font-weight: 600;
    font-size: 0.9rem;
}

.calendar-day {
    background: white;
    min-height: 120px;
    padding: 8px;
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
}

.calendar-day:hover {
    background: #D8F3DC;
}

.calendar-day.today {
    background: #B7E4C7;
    font-weight: bold;
}

.calendar-day.selected {
    background: #52B788;
    color: white;
}

.calendar-day.other-month {
    background: #f8f9fa;
    color: #adb5bd;
}

.day-number {
    font-weight: 600;
    margin-bottom: 5px;
    font-size: 0.95rem;
}

.day-appointments {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.appointment-preview {
    background: #52B788;
    color: white;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.7rem;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    justify-content: space-between;
}

.appointment-preview:hover {
    background: #2D6A4F;
}

.appointment-preview.emergency {
    background: #22577A;
}

.appointment-preview.surgery {
    background: #38A3A5;
}

.appointment-preview.vaccination {
    background: #52B788;
}

.more-appointments {
    font-size: 0.65rem;
    color: #666;
    text-align: center;
    margin-top: 2px;
}

/* Vista Semanal */
.week-day-header {
    background: white;
    padding: 15px 10px;
    text-align: center;
    border-bottom: 2px solid #B7E4C7;
}

.week-day-header.today {
    background: #D8F3DC;
    color: #2D6A4F;
}

.time-header, .time-slot {
    background: #2D6A4F;
    color: white;
    padding: 10px;
    text-align: center;
    font-size: 0.85rem;
    font-weight: 500;
}

.hour-slot, .day-hour-slot {
    background: white;
    min-height: 60px;
    padding: 5px;
    border-bottom: 1px solid #B7E4C7;
    position: relative;
}

.hour-slot.empty-slot, .day-hour-slot.empty-slot {
    cursor: pointer;
    transition: all 0.2s ease;
}

.hour-slot.empty-slot:hover, .day-hour-slot.empty-slot:hover {
    background: #D8F3DC;
}

.add-appointment {
    color: #52B788;
    font-size: 0.8rem;
    text-align: center;
    padding: 10px;
    opacity: 0.7;
}

.week-appointment, .day-appointment {
    background: #52B788;
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
    margin-bottom: 2px;
    cursor: pointer;
    font-size: 0.8rem;
    transition: all 0.2s ease;
}

.week-appointment:hover, .day-appointment:hover {
    background: #2D6A4F;
    transform: translateY(-1px);
}

.day-appointment {
    padding: 10px;
    margin-bottom: 5px;
}

.apt-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    font-weight: 600;
}

.apt-status {
    font-size: 0.7rem;
    background: rgba(255,255,255,0.2);
    padding: 2px 6px;
    border-radius: 10px;
}

.apt-patient {
    margin-bottom: 5px;
}

.species {
    font-size: 0.7rem;
    opacity: 0.8;
    margin-left: 5px;
}

.apt-owner, .apt-reason {
    font-size: 0.75rem;
    opacity: 0.9;
    margin-bottom: 3px;
}

.apt-actions {
    display: flex;
    gap: 5px;
    margin-top: 8px;
}

.btn-action.small {
    padding: 4px 6px;
    font-size: 0.7rem;
    background: rgba(255,255,255,0.2);
    border: none;
    border-radius: 3px;
    color: white;
    cursor: pointer;
}

.btn-action.small:hover {
    background: rgba(255,255,255,0.3);
}

/* Vista de Día */
.day-view-header {
    background: linear-gradient(135deg, #2D6A4F 0%, #22577A 100%);
    color: white;
    padding: 20px;
    text-align: center;
}

.day-title h3 {
    margin: 0 0 5px 0;
    font-size: 1.3rem;
}

.day-subtitle {
    opacity: 0.9;
    font-size: 0.9rem;
}

.calendar-loading {
    grid-column: 1 / -1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 20px;
    background: white;
    color: #52B788;
}

/* Tipos de citas */
.consultation { background: #52B788 !important; }
.surgery { background: #38A3A5 !important; }
.vaccination { background: #2D6A4F !important; }
.emergency { background: #22577A !important; }
.control { background: #B7E4C7 !important; color: #2D6A4F !important; }

/* Estados de citas */
.scheduled { opacity: 1; }
.confirmed { opacity: 1; box-shadow: 0 0 0 2px rgba(255,255,255,0.3); }
.in-progress { animation: pulse 2s infinite; }
.completed { opacity: 0.7; }
.cancelled { opacity: 0.5; text-decoration: line-through; }

@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(255,255,255,0.4); }
    70% { box-shadow: 0 0 0 10px rgba(255,255,255,0); }
    100% { box-shadow: 0 0 0 0 rgba(255,255,255,0); }
}

/* Responsivo */
@media (max-width: 768px) {
    .calendar-day {
        min-height: 80px;
        padding: 5px;
    }
    
    .day-number {
        font-size: 0.8rem;
    }
    
    .appointment-preview {
        font-size: 0.65rem;
        padding: 1px 4px;
    }
    
    .calendar-day-header {
        padding: 10px 5px;
        font-size: 0.8rem;
    }
}
</style>
`;

document.head.insertAdjacentHTML('beforeend', calendarStyles);