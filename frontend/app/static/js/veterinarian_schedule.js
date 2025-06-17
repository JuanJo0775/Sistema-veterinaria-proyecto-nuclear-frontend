// frontend/app/static/js/veterinarian_schedule.js

class VeterinarianSchedule {
    constructor() {
        this.scheduleData = {};
        this.daysOfWeek = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
        this.dayNames = {
            'monday': 'Lunes',
            'tuesday': 'Martes',
            'wednesday': 'Miércoles',
            'thursday': 'Jueves',
            'friday': 'Viernes',
            'saturday': 'Sábado',
            'sunday': 'Domingo'
        };
        this.dayIcons = {
            'monday': '📅',
            'tuesday': '📋',
            'wednesday': '🗓️',
            'thursday': '📆',
            'friday': '🗂️',
            'saturday': '📊',
            'sunday': '🏠'
        };
        this.init();
    }

    init() {
        console.log('🔧 Inicializando configuración de horarios...');
        this.loadScheduleData();
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Botones de guardar y resetear
        const saveBtn = document.querySelector('.save-btn.btn-primary');
        const resetBtn = document.querySelector('.save-btn.btn-secondary');

        if (saveBtn) saveBtn.addEventListener('click', () => this.saveSchedule());
        if (resetBtn) resetBtn.addEventListener('click', () => this.resetSchedule());

        // Setup global functions
        window.saveSchedule = () => this.saveSchedule();
        window.resetSchedule = () => this.resetSchedule();
        window.copyPreviousWeek = () => this.copyPreviousWeek();
        window.setDefaultHours = () => this.setDefaultHours();
    }

    async loadScheduleData() {
        try {
            this.showLoading();
            console.log('📊 Cargando datos de horario...');

            const response = await fetch('/api/veterinarian/schedule-data');
            const data = await response.json();

            if (data.success) {
                this.scheduleData = this.processScheduleData(data.schedules);
                this.renderSchedule();
                this.updateSummary();
                this.loadStats();
                console.log('✅ Horarios cargados exitosamente');
            } else {
                throw new Error(data.message || 'Error obteniendo horarios');
            }

        } catch (error) {
            console.error('❌ Error cargando horarios:', error);
            this.showError('Error cargando los horarios');
            this.renderEmptySchedule();
        } finally {
            this.hideLoading();
        }
    }

    processScheduleData(schedules) {
        const processedData = {};

        // Inicializar todos los días como inactivos
        this.daysOfWeek.forEach(day => {
            processedData[day] = {
                active: false,
                start_time: '09:00',
                end_time: '17:00',
                break_start: '12:00',
                break_end: '13:00'
            };
        });

        // Procesar horarios existentes
        schedules.forEach(schedule => {
            const dayName = this.getDayNameFromNumber(schedule.day_of_week);
            if (dayName && processedData[dayName]) {
                processedData[dayName] = {
                    active: schedule.is_available,
                    start_time: schedule.start_time,
                    end_time: schedule.end_time,
                    break_start: schedule.break_start || '12:00',
                    break_end: schedule.break_end || '13:00',
                    schedule_id: schedule.id
                };
            }
        });

        return processedData;
    }

    getDayNameFromNumber(dayNumber) {
        // Convertir número de día (0=Sunday, 1=Monday, etc.) a nombre
        const dayMap = {
            0: 'sunday',
            1: 'monday',
            2: 'tuesday',
            3: 'wednesday',
            4: 'thursday',
            5: 'friday',
            6: 'saturday'
        };
        return dayMap[dayNumber];
    }

    getDayNumberFromName(dayName) {
        const dayMap = {
            'sunday': 0,
            'monday': 1,
            'tuesday': 2,
            'wednesday': 3,
            'thursday': 4,
            'friday': 5,
            'saturday': 6
        };
        return dayMap[dayName];
    }

    renderSchedule() {
        const container = document.getElementById('weeklySchedule');
        if (!container) return;

        container.innerHTML = '';

        this.daysOfWeek.forEach(day => {
            const dayData = this.scheduleData[day];
            const dayElement = this.createDayElement(day, dayData);
            container.appendChild(dayElement);
        });
    }

    createDayElement(day, dayData) {
        const div = document.createElement('div');
        div.className = `day-schedule ${dayData.active ? 'active' : 'inactive'}`;
        div.setAttribute('data-day', day);

        div.innerHTML = `
            <div class="day-header">
                <div class="day-name">
                    <span class="day-icon">${this.dayIcons[day]}</span>
                    <span>${this.dayNames[day]}</span>
                </div>
                <div class="day-toggle ${dayData.active ? 'active' : ''}" onclick="toggleDay('${day}')">
                </div>
            </div>

            <div class="day-content" style="display: ${dayData.active ? 'block' : 'none'}">
                <div class="time-settings">
                    <div class="time-group">
                        <label class="time-label">Hora de inicio:</label>
                        <input type="time" class="time-input" data-field="start_time" data-day="${day}" 
                               value="${dayData.start_time}" onchange="updateDayTime('${day}', 'start_time', this.value)">
                    </div>
                    <div class="time-group">
                        <label class="time-label">Hora de fin:</label>
                        <input type="time" class="time-input" data-field="end_time" data-day="${day}" 
                               value="${dayData.end_time}" onchange="updateDayTime('${day}', 'end_time', this.value)">
                    </div>
                </div>

                <div class="break-settings">
                    <div class="break-header">
                        <span class="break-title">⏱️ Horario de almuerzo</span>
                    </div>
                    <div class="time-settings">
                        <div class="time-group">
                            <label class="time-label">Inicio almuerzo:</label>
                            <input type="time" class="time-input" data-field="break_start" data-day="${day}" 
                                   value="${dayData.break_start}" onchange="updateDayTime('${day}', 'break_start', this.value)">
                        </div>
                        <div class="time-group">
                            <label class="time-label">Fin almuerzo:</label>
                            <input type="time" class="time-input" data-field="break_end" data-day="${day}" 
                                   value="${dayData.break_end}" onchange="updateDayTime('${day}', 'break_end', this.value)">
                        </div>
                    </div>
                </div>

                <div class="day-summary">
                    <span class="working-hours">Horario: ${dayData.start_time} - ${dayData.end_time}</span>
                    <span class="total-hours">${this.calculateDayHours(dayData)} horas</span>
                </div>
            </div>
        `;

        return div;
    }

    calculateDayHours(dayData) {
        if (!dayData.active) return 0;

        const start = this.timeToMinutes(dayData.start_time);
        const end = this.timeToMinutes(dayData.end_time);
        const breakStart = this.timeToMinutes(dayData.break_start);
        const breakEnd = this.timeToMinutes(dayData.break_end);

        const totalMinutes = (end - start) - (breakEnd - breakStart);
        return (totalMinutes / 60).toFixed(1);
    }

    timeToMinutes(timeString) {
        const [hours, minutes] = timeString.split(':').map(Number);
        return hours * 60 + minutes;
    }

    toggleDay(day) {
        const dayData = this.scheduleData[day];
        dayData.active = !dayData.active;

        // Actualizar UI
        const dayElement = document.querySelector(`[data-day="${day}"]`);
        const toggle = dayElement.querySelector('.day-toggle');
        const content = dayElement.querySelector('.day-content');

        if (dayData.active) {
            dayElement.classList.remove('inactive');
            dayElement.classList.add('active');
            toggle.classList.add('active');
            content.style.display = 'block';
        } else {
            dayElement.classList.remove('active');
            dayElement.classList.add('inactive');
            toggle.classList.remove('active');
            content.style.display = 'none';
        }

        this.updateSummary();
    }

    updateDayTime(day, field, value) {
        this.scheduleData[day][field] = value;

        // Actualizar resumen del día
        const dayElement = document.querySelector(`[data-day="${day}"]`);
        const summaryElement = dayElement.querySelector('.day-summary');
        const dayData = this.scheduleData[day];

        summaryElement.innerHTML = `
            <span class="working-hours">Horario: ${dayData.start_time} - ${dayData.end_time}</span>
            <span class="total-hours">${this.calculateDayHours(dayData)} horas</span>
        `;

        this.updateSummary();
    }

    updateSummary() {
        const workingDays = Object.values(this.scheduleData).filter(day => day.active).length;
        const totalHours = Object.values(this.scheduleData)
            .filter(day => day.active)
            .reduce((total, day) => total + parseFloat(this.calculateDayHours(day)), 0);
        const dailyAverage = workingDays > 0 ? (totalHours / workingDays).toFixed(1) : 0;

        // Actualizar elementos del resumen
        const workingDaysEl = document.getElementById('workingDays');
        const weeklyHoursEl = document.getElementById('weeklyHours');
        const dailyAverageEl = document.getElementById('dailyAverage');

        if (workingDaysEl) workingDaysEl.textContent = workingDays;
        if (weeklyHoursEl) weeklyHoursEl.textContent = `${totalHours.toFixed(1)}h`;
        if (dailyAverageEl) dailyAverageEl.textContent = `${dailyAverage}h`;
    }

    async loadStats() {
        try {
            // Cargar estadísticas de citas
            const response = await fetch('/api/veterinarian/dashboard-data');
            const data = await response.json();

            if (data.success) {
                const todayEl = document.getElementById('todayAppointments');
                const weekEl = document.getElementById('weekAppointments');

                if (todayEl) todayEl.textContent = data.stats.today_appointments_count || 0;
                if (weekEl) weekEl.textContent = data.stats.week_appointments || 0;
            }
        } catch (error) {
            console.error('Error cargando estadísticas:', error);
        }
    }

    async saveSchedule() {
        try {
            this.showSaving();

            const scheduleArray = this.convertToAPIFormat();

            const response = await fetch('/api/veterinarian/save-schedule', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    schedules: scheduleArray
                })
            });

            const result = await response.json();

            if (result.success) {
                this.showSuccess('Horario guardado exitosamente');
                // Recargar datos
                await this.loadScheduleData();
            } else {
                throw new Error(result.message || 'Error guardando horario');
            }

        } catch (error) {
            console.error('Error guardando horario:', error);
            this.showError('Error guardando el horario');
        } finally {
            this.hideSaving();
        }
    }

    convertToAPIFormat() {
        const scheduleArray = [];

        Object.entries(this.scheduleData).forEach(([day, data]) => {
            scheduleArray.push({
                day_of_week: this.getDayNumberFromName(day),
                start_time: data.start_time,
                end_time: data.end_time,
                break_start: data.break_start,
                break_end: data.break_end,
                is_available: data.active,
                schedule_id: data.schedule_id || null
            });
        });

        return scheduleArray;
    }

    resetSchedule() {
        if (confirm('¿Estás seguro de que deseas restablecer el horario?')) {
            this.loadScheduleData();
        }
    }

    copyPreviousWeek() {
        // Implementar lógica para copiar horario de semana anterior
        this.showInfo('Función de copiar semana anterior en desarrollo');
    }

    setDefaultHours() {
        // Establecer horarios por defecto (9:00 - 17:00, Lunes a Viernes)
        const defaultDays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'];

        defaultDays.forEach(day => {
            this.scheduleData[day] = {
                active: true,
                start_time: '09:00',
                end_time: '17:00',
                break_start: '12:00',
                break_end: '13:00'
            };
        });

        // Desactivar fines de semana
        this.scheduleData.saturday.active = false;
        this.scheduleData.sunday.active = false;

        this.renderSchedule();
        this.updateSummary();
        this.showInfo('Horarios por defecto establecidos');
    }

    renderEmptySchedule() {
        const container = document.getElementById('weeklySchedule');
        if (!container) return;

        container.innerHTML = `
            <div class="empty-schedule">
                <div class="empty-icon">⏰</div>
                <div class="empty-title">No se pudo cargar el horario</div>
                <div class="empty-message">Verifica tu conexión e intenta nuevamente</div>
                <button class="btn-retry" onclick="window.location.reload()">🔄 Reintentar</button>
            </div>
        `;
    }

    showLoading() {
        const loading = document.querySelector('.loading-calendar');
        if (loading) loading.style.display = 'block';
    }

    hideLoading() {
        const loading = document.querySelector('.loading-calendar');
        if (loading) loading.style.display = 'none';
    }

    showSaving() {
        const saveBtn = document.querySelector('.save-btn.btn-primary');
        if (saveBtn) {
            saveBtn.disabled = true;
            saveBtn.innerHTML = '⏳ Guardando...';
        }
    }

    hideSaving() {
        const saveBtn = document.querySelector('.save-btn.btn-primary');
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '💾 Guardar Horario';
        }
    }

    showSuccess(message) {
        this.showToast(message, 'success');
    }

    showError(message) {
        this.showToast(message, 'error');
    }

    showInfo(message) {
        this.showToast(message, 'info');
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

// Funciones globales
window.toggleDay = function(day) {
    if (window.veterinarianSchedule) {
        window.veterinarianSchedule.toggleDay(day);
    }
};

window.updateDayTime = function(day, field, value) {
    if (window.veterinarianSchedule) {
        window.veterinarianSchedule.updateDayTime(day, field, value);
    }
};

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    window.veterinarianSchedule = new VeterinarianSchedule();
});

// CSS adicional para horarios
const scheduleStyles = `
<style>
.empty-schedule {
    text-align: center;
    padding: 60px 20px;
    color: #666;
}

.empty-icon {
    font-size: 3rem;
    margin-bottom: 20px;
}

.empty-title {
    font-size: 1.2rem;
    font-weight: 600;
    margin-bottom: 10px;
    color: #2D6A4F;
}

.empty-message {
    margin-bottom: 20px;
    color: #666;
}

.btn-retry {
    background: #52B788;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 500;
    transition: all 0.3s ease;
}

.btn-retry:hover {
    background: #2D6A4F;
    transform: translateY(-2px);
}

.toast-success {
    background: #d4edda;
    border: 1px solid #c3e6cb;
    color: #155724;
}

.toast-info {
    background: #d1ecf1;
    border: 1px solid #bee5eb;
    color: #0c5460;
}

.break-settings {
    margin-top: 15px;
    padding-top: 15px;
    border-top: 1px solid #B7E4C7;
}

.break-header {
    margin-bottom: 10px;
}

.break-title {
    font-size: 0.9rem;
    color: #2D6A4F;
    font-weight: 500;
}

.day-summary {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 15px;
    padding-top: 10px;
    border-top: 1px solid #B7E4C7;
    font-size: 0.85rem;
}

.working-hours {
    color: #2D6A4F;
    font-weight: 500;
}

.total-hours {
    background: #52B788;
    color: white;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.8rem;
    font-weight: 600;
}
</style>
`;

document.head.insertAdjacentHTML('beforeend', scheduleStyles);