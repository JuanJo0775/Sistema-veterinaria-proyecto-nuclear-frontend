// frontend/app/static/js/veterinarian_dashboard.js

class VeterinarianDashboard {
    constructor() {
        this.API_BASE = '';
        this.init();
    }

    init() {
        console.log('🔧 Inicializando Dashboard del Veterinario...');
        this.loadDashboardData();
        this.setupEventListeners();
        this.setupAutoRefresh();
    }

    setupEventListeners() {
        // Refresh button
        const refreshBtn = document.getElementById('refreshDashboard');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadDashboardData();
            });
        }

        // Card clicks for navigation
        this.setupCardNavigation();
    }

    setupCardNavigation() {
        // Hacer las tarjetas clickeables
        const cards = document.querySelectorAll('.stat-card');
        cards.forEach(card => {
            card.style.cursor = 'pointer';
            card.addEventListener('click', function() {
                const onclick = this.getAttribute('onclick');
                if (onclick) {
                    eval(onclick);
                }
            });
        });
    }

    setupAutoRefresh() {
        // Refrescar datos cada 5 minutos
        setInterval(() => {
            this.loadDashboardData(false); // false = sin loading indicator
        }, 5 * 60 * 1000);
    }

    async loadDashboardData(showLoading = true) {
        try {
            if (showLoading) {
                this.showLoading();
            }

            console.log('📊 Cargando datos del dashboard...');
            const response = await fetch('/api/veterinarian/dashboard-data');
            const data = await response.json();

            if (data.success) {
                this.renderDashboardData(data);
                console.log('✅ Datos del dashboard cargados exitosamente');
            } else {
                throw new Error(data.message || 'Error obteniendo datos');
            }

        } catch (error) {
            console.error('❌ Error cargando dashboard:', error);
            this.showError('Error cargando los datos del dashboard');
        } finally {
            this.hideLoading();
        }
    }

    renderDashboardData(data) {
        // Actualizar nombre del veterinario
        this.updateVeterinarianName(data.user_info);

        // Actualizar estadísticas
        this.updateStats(data.stats);

        // Actualizar citas de hoy
        this.updateTodayAppointments(data.today_appointments);

        // Actualizar pacientes recientes
        this.updateRecentPatients(data.recent_patients);
    }

    updateVeterinarianName(userInfo) {
        const welcomeTitle = document.querySelector('.welcome-title');
        const userName = document.querySelector('.user-name');
        const userInitial = document.querySelector('.user-initial');

        if (welcomeTitle && userInfo.name) {
            welcomeTitle.textContent = `¡Bienvenido, Dr. ${userInfo.name}!`;
        }

        if (userName && userInfo.name) {
            userName.textContent = userInfo.name;
        }

        if (userInitial && userInfo.initial) {
            userInitial.textContent = userInfo.initial;
        }
    }

    updateStats(stats) {
        // Actualizar contadores
        this.updateCounter('todayAppointments', stats.today_appointments_count);
        this.updateCounter('totalPatients', stats.total_patients);
        this.updateCounter('pendingRecords', stats.pending_records);
        this.updateCounter('completedToday', stats.completed_today);
    }

    updateCounter(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            const currentValue = parseInt(element.textContent) || 0;
            this.animateCounter(element, currentValue, value);
        }
    }

    animateCounter(element, start, end) {
        const duration = 1000; // 1 segundo
        const startTime = performance.now();

        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);

            const currentValue = Math.floor(start + (end - start) * progress);
            element.textContent = currentValue;

            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };

        requestAnimationFrame(animate);
    }

    updateTodayAppointments(appointments) {
        const container = document.getElementById('todayAppointmentsList');
        if (!container) return;

        container.innerHTML = '';

        if (appointments.length === 0) {
            container.innerHTML = `
                <div class="no-appointments">
                    <div class="no-data-icon">📅</div>
                    <div class="no-data-text">No tienes citas programadas para hoy</div>
                    <a href="/veterinarian/calendar" class="no-data-action">Ver calendario completo</a>
                </div>
            `;
            return;
        }

        appointments.forEach(appointment => {
            const appointmentEl = this.createAppointmentElement(appointment);
            container.appendChild(appointmentEl);
        });
    }

    createAppointmentElement(appointment) {
        const div = document.createElement('div');
        div.className = 'appointment-item';

        const statusClass = this.getStatusClass(appointment.status);
        const statusText = this.getStatusText(appointment.status);

        div.innerHTML = `
            <div class="appointment-time">${appointment.appointment_time}</div>
            <div class="appointment-details">
                <div class="patient-name">${appointment.pet_name || 'Mascota'}</div>
                <div class="owner-name">Propietario: ${appointment.owner_name || 'No especificado'}</div>
                <div class="appointment-reason">${appointment.reason || 'Consulta general'}</div>
            </div>
            <div class="appointment-status">
                <span class="status-badge ${statusClass}">${statusText}</span>
            </div>
            <div class="appointment-actions">
                <button class="btn-action view" onclick="viewAppointment('${appointment.id}')" title="Ver detalles">
                    👁️
                </button>
                ${appointment.status === 'scheduled' ? `
                    <button class="btn-action edit" onclick="editAppointment('${appointment.id}')" title="Editar">
                        ✏️
                    </button>
                ` : ''}
            </div>
        `;

        return div;
    }

    updateRecentPatients(patients) {
        const container = document.getElementById('recentPatientsGrid');
        if (!container) return;

        container.innerHTML = '';

        if (patients.length === 0) {
            container.innerHTML = `
                <div class="no-patients">
                    <div class="no-data-icon">🐕</div>
                    <div class="no-data-text">No hay pacientes recientes</div>
                    <a href="/veterinarian/patients" class="no-data-action">Ver todos los pacientes</a>
                </div>
            `;
            return;
        }

        patients.forEach(patient => {
            const patientEl = this.createPatientElement(patient);
            container.appendChild(patientEl);
        });
    }

    createPatientElement(patient) {
        const div = document.createElement('div');
        div.className = 'patient-card';

        const lastVisit = patient.last_visit ? new Date(patient.last_visit).toLocaleDateString() : 'No registrado';

        div.innerHTML = `
            <div class="patient-avatar">
                ${patient.photo_url ? 
                    `<img src="${patient.photo_url}" alt="${patient.name}">` : 
                    `<div class="patient-initial">${patient.name ? patient.name[0].toUpperCase() : '🐕'}</div>`
                }
            </div>
            <div class="patient-info">
                <div class="patient-name">${patient.name || 'Sin nombre'}</div>
                <div class="patient-species">${patient.species || 'No especificado'} ${patient.breed ? `- ${patient.breed}` : ''}</div>
                <div class="patient-age">${patient.age ? `${patient.age} años` : 'Edad no registrada'}</div>
                <div class="patient-last-visit">Última visita: ${lastVisit}</div>
            </div>
            <div class="patient-actions">
                <button class="btn-action" onclick="viewPatientHistory('${patient.id}')" title="Ver historia clínica">
                    📋
                </button>
            </div>
        `;

        // Hacer clickeable toda la tarjeta
        div.addEventListener('click', () => {
            window.location.href = `/veterinarian/patients/${patient.id}`;
        });

        return div;
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

    showLoading() {
        const loadingElements = document.querySelectorAll('.loading');
        loadingElements.forEach(el => {
            el.style.display = 'block';
        });

        // Ocultar contenido mientras se carga
        const contentElements = document.querySelectorAll('.appointment-list, .patients-grid');
        contentElements.forEach(el => {
            el.style.opacity = '0.5';
        });
    }

    hideLoading() {
        const loadingElements = document.querySelectorAll('.loading');
        loadingElements.forEach(el => {
            el.style.display = 'none';
        });

        // Mostrar contenido
        const contentElements = document.querySelectorAll('.appointment-list, .patients-grid');
        contentElements.forEach(el => {
            el.style.opacity = '1';
        });
    }

    showError(message) {
        // Crear toast de error
        const toast = document.createElement('div');
        toast.className = 'toast toast-error';
        toast.innerHTML = `
            <div class="toast-content">
                <span class="toast-icon">❌</span>
                <span class="toast-message">${message}</span>
            </div>
        `;

        document.body.appendChild(toast);

        // Auto-remove después de 5 segundos
        setTimeout(() => {
            toast.remove();
        }, 5000);
    }
}

// Funciones globales para los botones de acción
window.viewAppointment = function(appointmentId) {
    window.location.href = `/veterinarian/appointments/${appointmentId}`;
};

window.editAppointment = function(appointmentId) {
    window.location.href = `/veterinarian/appointments/${appointmentId}/edit`;
};

window.viewPatientHistory = function(patientId) {
    window.location.href = `/veterinarian/patients/${patientId}/history`;
};

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    window.veterinarianDashboard = new VeterinarianDashboard();
});

// CSS adicional para los elementos dinámicos
const additionalStyles = `
<style>
.appointment-item {
    display: flex;
    align-items: center;
    padding: 15px;
    border: 1px solid #B7E4C7;
    border-radius: 10px;
    margin-bottom: 10px;
    transition: all 0.3s ease;
    background: white;
}

.appointment-item:hover {
    border-color: #52B788;
    box-shadow: 0 2px 8px rgba(82, 183, 136, 0.1);
}

.appointment-time {
    font-weight: bold;
    color: #2D6A4F;
    font-size: 1.1rem;
    min-width: 80px;
}

.appointment-details {
    flex: 1;
    margin-left: 15px;
}

.patient-name {
    font-weight: 600;
    color: #081C15;
    margin-bottom: 2px;
}

.owner-name, .appointment-reason {
    font-size: 0.9rem;
    color: #666;
    margin-bottom: 2px;
}

.status-badge {
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 0.8rem;
    font-weight: 500;
}

.status-badge.scheduled { background: #D8F3DC; color: #2D6A4F; }
.status-badge.confirmed { background: #B7E4C7; color: #2D6A4F; }
.status-badge.in-progress { background: #38A3A5; color: white; }
.status-badge.completed { background: #52B788; color: white; }
.status-badge.cancelled { background: #ffebee; color: #c62828; }

.appointment-actions {
    display: flex;
    gap: 5px;
}

.btn-action {
    background: none;
    border: 1px solid #B7E4C7;
    border-radius: 6px;
    padding: 6px 8px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.btn-action:hover {
    background: #B7E4C7;
}

.patient-card {
    display: flex;
    align-items: center;
    padding: 15px;
    border: 1px solid #B7E4C7;
    border-radius: 10px;
    margin-bottom: 10px;
    transition: all 0.3s ease;
    background: white;
    cursor: pointer;
}

.patient-card:hover {
    border-color: #52B788;
    box-shadow: 0 2px 8px rgba(82, 183, 136, 0.1);
    transform: translateY(-1px);
}

.patient-avatar {
    width: 50px;
    height: 50px;
    border-radius: 50%;
    overflow: hidden;
    margin-right: 15px;
    background: #D8F3DC;
    display: flex;
    align-items: center;
    justify-content: center;
}

.patient-avatar img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.patient-initial {
    font-size: 1.2rem;
    font-weight: bold;
    color: #2D6A4F;
}

.patient-info {
    flex: 1;
}

.patient-name {
    font-weight: 600;
    color: #081C15;
    margin-bottom: 4px;
}

.patient-species, .patient-age, .patient-last-visit {
    font-size: 0.85rem;
    color: #666;
    margin-bottom: 2px;
}

.no-appointments, .no-patients {
    text-align: center;
    padding: 40px 20px;
    color: #666;
}

.no-data-icon {
    font-size: 2rem;
    margin-bottom: 10px;
}

.no-data-text {
    margin-bottom: 15px;
    font-size: 0.95rem;
}

.no-data-action {
    color: #52B788;
    text-decoration: none;
    font-weight: 500;
}

.no-data-action:hover {
    text-decoration: underline;
}

.toast {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 9999;
    min-width: 300px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    animation: slideIn 0.3s ease;
}

.toast-error {
    background: #ffebee;
    border: 1px solid #ffcdd2;
    color: #c62828;
}

.toast-content {
    display: flex;
    align-items: center;
    padding: 12px 16px;
}

.toast-icon {
    margin-right: 10px;
}

@keyframes slideIn {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

.loading {
    display: none;
    text-align: center;
    padding: 20px;
    color: #52B788;
}

.spinner {
    border: 3px solid #D8F3DC;
    border-top: 3px solid #52B788;
    border-radius: 50%;
    width: 30px;
    height: 30px;
    animation: spin 1s linear infinite;
    margin: 0 auto 10px;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
</style>
`;

// Inyectar estilos adicionales
document.head.insertAdjacentHTML('beforeend', additionalStyles);