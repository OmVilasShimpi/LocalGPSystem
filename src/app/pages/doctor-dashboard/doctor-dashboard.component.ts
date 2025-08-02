import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { NgxMaterialTimepickerModule } from 'ngx-material-timepicker';

@Component({
  selector: 'app-doctor-dashboard',
  templateUrl: './doctor-dashboard.component.html',
  styleUrls: ['./doctor-dashboard.component.css'],
  standalone: true,
  imports: [CommonModule, FormsModule,NgxMaterialTimepickerModule]
})
export class DoctorDashboardComponent implements OnInit {
  //  Doctor data and form
  doctorData: any = {};
  updatedData = { specialization: '', experience: '', clinic_address: '', registration_no: '' };

  //  Slot input
  newSlot = { date: '', start_time: '', end_time: '' };

  // Appointment & Prescription State
  upcomingAppointments: any[] = [];
  filteredAppointments: any[] = [];
  uniquePatients: any[] = [];
  patientAppointments: any[] = [];
  selectedAppointmentForPrescription: any = null;
  prescriptionText: string = '';
  prescriptionInstructions: string ='';
  prescriptionsMap: { [id: number]: boolean } = {};
  prescriptionLoaded: boolean = false;

  // Selected Patient Info
  selectedPatientId: number | null = null;
  selectedPharmacyId: number | null = null;
  patientPrescriptions: any[] = [];
  selectedPatientName: string = '';

  // medical history for doctor
  medicalForm = {
    diagnosis: '',
    treatment: '',
    medicines: '',
    notes: ''
  };
  
  showMedicalHistoryForm: boolean = false;
  timer: any;
  weeklySlots: any[] = [];

  //  UI State
  showProfileForm = false;
  isProfileComplete = false;
  today = '';
  currentTime = '';
  searchQuery = '';
  successMessage = '';
  errorMessage = '';
  infoMessage = '';
  timeValidationMessage: string = '';

  stats = { totalPatients: 0, totalSlots: 0, completedAppointments: 0 };

  constructor(private http: HttpClient, private router: Router) {}

  ngOnInit(): void {
    const token = this.getToken();
    this.today = this.getTodayDate();
    this.startClock();

    if (token) {
      this.getDoctorDetails(token);
      this.loadAppointments(token);
      this.fetchStats(token);
    } else {
      this.showError('Unauthorized access. Redirecting to login.');
      this.router.navigate(['/login']);
    }
  }

  getTodayDate(): string {
    return new Date().toISOString().split('T')[0];
  }

  getToken(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('token');
    }
    return null; // In server-side rendering, no token
  }
  
  getAuthHeaders() {
    return { headers: { Authorization: `Bearer ${this.getToken()}` } };
  }

  startClock(): void {
    this.timer = setInterval(() => {
      this.currentTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }, 1000);
  }
  ngOnDestroy(): void {
    if (this.timer) {
      clearInterval(this.timer);
    }
  }  
  getDoctorDetails(token: string): void {
    this.http.get('http://127.0.0.1:5000/user/details', this.getAuthHeaders()).subscribe({
      next: (res: any) => {
        this.doctorData = res;
        this.doctorData.name = res.name;
        const { specialization, experience, clinic_address, registration_no } = res;
        this.updatedData = { specialization, experience, clinic_address, registration_no };
        this.isProfileComplete = specialization && experience && clinic_address && registration_no;
        this.showProfileForm = !this.isProfileComplete;
      },
      error: () => this.showError('Failed to load profile. Please try again.')
    });
  }

  updateProfile(): void {
    this.http.post('http://127.0.0.1:5000/user/update-doctor-profile', this.updatedData, this.getAuthHeaders())
      .subscribe({
        next: () => {
          this.showSuccess(' Profile updated!');
          this.showProfileForm = false;
          this.ngOnInit();
        },
        error: () => this.showError(' Update failed.')
      });
  }
  validateSlotTime(): void {
    setTimeout(() => {
      const start = this.newSlot.start_time;
      const end = this.newSlot.end_time;
  
      if (!start || !end) {
        this.timeValidationMessage = '';
        return;
      }
  
      const [startHour, startMin] = start.split(':').map(Number);
      const [endHour, endMin] = end.split(':').map(Number);
  
      const startTotalMinutes = startHour * 60 + startMin;
      const endTotalMinutes = endHour * 60 + endMin;
  
      const minAllowedMinutes = 6 * 60;   // 06:00 AM
      const maxAllowedMinutes = 23 * 60;  // 11:00 PM
  
      if (startTotalMinutes < minAllowedMinutes) {
        this.timeValidationMessage = ' Start time must be after 06:00 AM.';
      } else if (endTotalMinutes > maxAllowedMinutes) {
        this.timeValidationMessage = ' End time must be before 11:00 PM.';
      } else if (startTotalMinutes >= endTotalMinutes) {
        this.timeValidationMessage = ' End time must be after start time.';
      } else {
        this.timeValidationMessage = '';
      }
    }, 0);
  }  
  addSlot(): void {
    const minAllowed = '06:00';
    const maxAllowed = '23:00';
  
    if (
      !this.newSlot.date ||
      !this.newSlot.start_time ||
      !this.newSlot.end_time ||
      this.newSlot.start_time >= this.newSlot.end_time
    ) {
      this.showError(' Please fill in a valid slot with proper time range.');
      return;
    }
  
    if (this.newSlot.start_time < minAllowed) {
      this.showError(' Start time must be after 06:00 AM.');
      return;
    }
  
    if (this.newSlot.end_time > maxAllowed) {
      this.showError(' End time must be before 11:00 PM.');
      return;
    }
  
    this.http.post('http://127.0.0.1:5000/appointments/add-slot', this.newSlot, this.getAuthHeaders())
      .subscribe({
        next: () => {
          this.showSuccess(' Slot added!');
          this.newSlot = { date: '', start_time: '', end_time: '' };
          this.loadAppointments(this.getToken()!);
          this.fetchStats(this.getToken()!);
        },
        error: () => this.showError(' Failed to add slot.')
      });
  }
  loadAppointments(token: string): void {
  this.http.get<any>('http://127.0.0.1:5000/appointments/upcoming-appointments', this.getAuthHeaders())
    .subscribe({
      next: res => {
        console.log(" Raw Appointments from backend:", res.appointments); 
        this.upcomingAppointments = res.appointments;
        //  Don't prefilter by status here — let grouping handle it properly
        this.groupAppointmentsByLatest();  // includes 'booked' + 'completed'
      },
      error: () => this.showError('Failed to fetch appointments.')
    });
}
  filterAppointments(): void {
  const q = this.searchQuery.toLowerCase();

  if (!q.trim()) {
    this.groupAppointmentsByLatest();  // restore full view if no search
    return;
  }

  const filtered = this.upcomingAppointments.filter(appt =>
    (appt.patient_name?.toLowerCase().includes(q) || '') ||
    (appt.status?.toLowerCase().includes(q) || '')
  );

  this.groupAppointmentsByLatest(filtered);
}
  groupAppointmentsByLatest(sourceAppointments: any[] = this.upcomingAppointments): void {
  const latestAppointments: { [patient_id: number]: any } = {};

  for (const appt of sourceAppointments) {
    if (!appt.patient_id || !appt.date || !appt.start_time) continue;

    const paddedTime = this.padTime(appt.start_time);
    const normalizedDate = new Date(appt.date).toISOString().split('T')[0];
    const currentTime = new Date(`${normalizedDate}T${paddedTime}`);

    if (isNaN(currentTime.getTime())) continue;

    const existing = latestAppointments[appt.patient_id];

    if (!existing) {
      latestAppointments[appt.patient_id] = appt;
      continue;
    }

    const existingPadded = this.padTime(existing.start_time);
    const existingDate = new Date(existing.date).toISOString().split('T')[0];
    const existingTime = new Date(`${existingDate}T${existingPadded}`);

    const currentIsBooked = appt.status === 'booked';
    const existingIsBooked = existing.status === 'booked';

    let preferCurrent = false;

    //  Highest priority: booked overrides completed even if older
    if (currentIsBooked && !existingIsBooked) {
      preferCurrent = true;
    }
    //  Next: if both same status, take latest
    else if (currentIsBooked === existingIsBooked && currentTime > existingTime) {
      preferCurrent = true;
    }

    if (preferCurrent) {
      latestAppointments[appt.patient_id] = appt;
    }
  }

  this.filteredAppointments = Object.values(latestAppointments);
  console.log(" Grouped (booked always prioritized):", this.filteredAppointments);
}
  markCompleted(appointmentId: number): void {
    if (!this.prescriptionsMap[appointmentId]) {
      this.showError("Please write a prescription first.");
      return;
    }

    this.http.put(`http://127.0.0.1:5000/appointments/complete/${appointmentId}`, {}, this.getAuthHeaders())
      .subscribe({
        next: () => {
          this.showSuccess(' Marked as completed.');
          this.loadAppointments(this.getToken()!);
        },
        error: () => this.showError(' Could not complete appointment.')
      });
  }

  openPrescriptionForm(appt: any): void {
    this.selectedAppointmentForPrescription = appt;
    this.prescriptionText = '';
    this.prescriptionInstructions = '';
    this.prescriptionLoaded = false;
  
    this.http.get<any>(`http://127.0.0.1:5000/prescriptions/by-appointment/${appt.id}`, this.getAuthHeaders())
      .subscribe({
        next: res => {
          if (res.prescription) {
            this.prescriptionText = res.prescription.medicines;
            this.prescriptionInstructions = res.prescription.instructions || '';
            this.prescriptionsMap[appt.id] = true;
          } else {
            this.prescriptionsMap[appt.id] = false;
          }
          this.prescriptionLoaded = true;
        },
        error: () => {
          this.prescriptionsMap[appt.id] = false;
          this.prescriptionLoaded = true;
        }
      });
  }
  

  savePrescription(): void {
    const appt = this.selectedAppointmentForPrescription;
    if (!appt || !this.prescriptionText.trim()) {
      this.showError("Please enter prescription.");
      return;
    }
  
    if (!this.selectedPharmacyId) {
      this.showInfo(" Patient has no pharmacy selected. Prescription will be created without linking pharmacy."); 
    }
  
    const payload = {
      appointment_id: appt.id,
      doctor_id: this.doctorData?.id,
      patient_id: appt.patient_id || this.selectedPatientId,
      pharmacy_id: this.selectedPharmacyId, // if null, backend will now try match based on address
      medicines: this.prescriptionText,
      instructions: this.prescriptionInstructions,
      status: 'Ready for Pickup',
      payment_note: ''
    };
  
    this.http.post('http://127.0.0.1:5000/prescriptions/add', payload, this.getAuthHeaders())
      .subscribe({
        next: () => {
          this.showSuccess(" Prescription saved!");
          this.prescriptionsMap[appt.id] = true;
          this.selectedAppointmentForPrescription = null;
          this.loadAppointments(this.getToken()!);
          this.openPatientDetails(this.selectedPatientId!); 
          this.loadAppointments(this.getToken()!); 
        },
        error: () => this.showError(" Failed to save prescription.")
      });
  }
  
  fetchStats(token: string): void {
    this.http.get<any>('http://127.0.0.1:5000/appointments/doctor/stats', this.getAuthHeaders())
      .subscribe({
        next: (res) => {
          this.stats = {
            totalPatients: res.total_patients,
            totalSlots: res.slots_this_week,
            completedAppointments: res.completed_appointments
          };
  
          //  Ensure the backend provides weekly slot info
          this.weeklySlots = res.weekly_slots || [];
        },
        error: () => {
          this.showError('Failed to load dashboard stats.');
        }
      });
  }
  downloadMedicalHistoryPDF(patientId: number): void {
  this.http.get(`http://127.0.0.1:5000/medical-history/download-all/${patientId}`, {
    ...this.getAuthHeaders(),
    responseType: 'blob' as 'json'
  }).subscribe({
    next: (pdfBlob: any) => {
      const blob = new Blob([pdfBlob], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'full_medical_history.pdf';
      a.click();
      URL.revokeObjectURL(url);
    },
    error: () => this.showError(" Failed to download full medical history.")
  });
}
  viewMedicalHistory(patientId: number): void {
    this.http.get<any[]>(`http://127.0.0.1:5000/medical-history/patient/${patientId}`, this.getAuthHeaders())
      .subscribe({
        next: (history) => {
          if (!history.length) {
            this.showInfo("No medical history available.");
            return;
          }
          const latestEntryId = history[0].id;
         window.open(`http://127.0.0.1:5000/medical-history/view/${patientId}`, '_blank');
        },
        error: () => this.showError("Failed to fetch medical history.")
      });
  }
  getSpecialtyIcon(specialty: string): string {
    const icons: any = {
      Cardiologist: '🫀',
      Dermatologist: '🧴',
      Pediatrician: '🧸',
      Neurologist: '🧠'
    };
    return icons[specialty] || '🩺';
  }  
  
  calculateSlotDuration(): string {
    try {
      if (!this.newSlot.start_time || !this.newSlot.end_time) return '';
  
      const start = this.convertTo24HourFormat(this.newSlot.start_time);
      const end = this.convertTo24HourFormat(this.newSlot.end_time);
  
      const startDate = new Date(0, 0, 0, start.hour, start.minute);
      const endDate = new Date(0, 0, 0, end.hour, end.minute);
  
      const diffMs = endDate.getTime() - startDate.getTime();
      if (diffMs <= 0) return '';
  
      const minutes = diffMs / 60000;
      const hrs = Math.floor(minutes / 60);
      const mins = Math.floor(minutes % 60);
  
      return `${hrs > 0 ? hrs + ' hr ' : ''}${mins} min`;
    } catch (err) {
      return '';
    }
  }
  
  convertTo24HourFormat(timeStr: string): { hour: number, minute: number } {
    const [time, modifier] = timeStr.split(' ');
    let [hours, minutes] = time.split(':').map(Number);
  
    if (modifier === 'PM' && hours < 12) {
      hours += 12;
    }
    if (modifier === 'AM' && hours === 12) {
      hours = 0;
    }
    return { hour: hours, minute: minutes };
  }
  onTimeSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    input.blur(); // auto closes the picker
  }  
  openPatientDetails(patientId: number): void {
  this.selectedPatientId = patientId;
  // Use latest appointment (even if not visible in upcomingAppointments)
  const appt = this.filteredAppointments.find(a => a.patient_id === patientId);
  this.selectedPatientName = appt?.patient_name || 'Patient';

  this.http.get<any>(`http://127.0.0.1:5000/appointments/all-for-patient/${patientId}`, this.getAuthHeaders())
    .subscribe({
      next: res => {
        this.patientAppointments = res.appointments || [];

        // Optional: sort them descending by date+time
        this.patientAppointments.sort((a: any, b: any) => {
          const dateA = new Date(`${a.date}T${a.start_time}`);
          const dateB = new Date(`${b.date}T${b.start_time}`);
          return dateB.getTime() - dateA.getTime();
        });
      },
      error: () => {
        this.showError(" Failed to load full appointment history.");
        this.patientAppointments = [];
      }
    });
} 
  closePatientDetails(): void {
    this.selectedPatientId = null;
    this.patientAppointments = [];
    this.patientPrescriptions = [];
    this.selectedPatientName = '';
  }
  
  isToday(dateStr: string): boolean {
    const today = new Date().toISOString().split('T')[0];
    return dateStr === today;
  }
  
  isTomorrow(dateStr: string): boolean {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    return dateStr === tomorrow.toISOString().split('T')[0];
  }
  
  isOverdue(appt: any): boolean {
    const apptDateTime = new Date(appt.date + ' ' + appt.end_time);
    return appt.status !== 'completed' && apptDateTime < new Date();
  }
  padTime(time: string): string {
  // Converts "6:30:00" → "06:30:00"
  const parts = time.split(':');
  if (parts.length === 3) {
    parts[0] = parts[0].padStart(2, '0');
    return parts.join(':');
  }
  return time;
}
  getTimeDistance(appt: any): string {
  if (!appt?.date || !appt?.start_time) return '';

  const paddedTime = this.padTime(appt.start_time);
  const datePart = new Date(appt.date).toISOString().split('T')[0];
  const apptTime = new Date(`${datePart}T${paddedTime}`);
  const now = new Date();

  if (isNaN(apptTime.getTime())) return ' Invalid time';

  const diffMs = apptTime.getTime() - now.getTime();
  const minutes = Math.round(diffMs / 60000);
  const hours = Math.floor(diffMs / (1000 * 60 * 60));
  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (Math.abs(minutes) < 5) return ' Ongoing now';
  if (minutes > 0 && minutes < 60) return ` Starts in ${minutes} min`;
  if (minutes >= 60 && hours < 24) return `Starts in ${hours} hr`;
  if (hours >= 24) return ` Starts in ${days} day${days !== 1 ? 's' : ''}`;
  if (minutes < 0 && Math.abs(minutes) < 60) return ` ${Math.abs(minutes)} min ago`;
  if (hours < 0 && Math.abs(hours) < 24) return ` ${Math.abs(hours)} hr ago`;
  return ` ${Math.abs(days)} day${Math.abs(days) !== 1 ? 's' : ''} ago`;
}
  openMedicalHistoryForm(): void {
    this.showMedicalHistoryForm = true;
    this.medicalForm = { diagnosis: '', treatment: '', medicines: '', notes: '' }; // reset
  }
  saveMedicalHistory(): void {
    if (!this.selectedPatientId) {
      this.showError('No patient selected.');
      return;
    }
  
    const payload = {
      patient_id: this.selectedPatientId,
      diagnosis: this.medicalForm.diagnosis,
      treatment: this.medicalForm.treatment,
      medicines: this.medicalForm.medicines,
      notes: this.medicalForm.notes
    };
  
    this.http.post<any>('http://127.0.0.1:5000/medical-history/add', payload, this.getAuthHeaders())
      .subscribe({
        next: (res) => {
          this.showSuccess(' Medical history saved!');
          this.showMedicalHistoryForm = false;
          if (res.entry_id) {
            window.open(`http://127.0.0.1:5000/medical-history/view/${this.selectedPatientId}`, '_blank');
          } else {
            this.openPatientDetails(this.selectedPatientId!); // fallback refresh
          }
        },
        error: () => {
          this.showError(' Failed to save medical history.');
        }
      });
  }
  logout(): void {
    const confirmLogout = confirm('⚠️ Are you sure you want to logout?');
    if (confirmLogout) {
      localStorage.clear();
      this.router.navigate(['/']);
    }
  }
  private showSuccess(msg: string) { this.successMessage = msg; this.clearMessages(); }
  private showError(msg: string) { this.errorMessage = msg; this.clearMessages(); }
  private showInfo(msg: string) { this.infoMessage = msg; this.clearMessages(); }
  private clearMessages() {
    setTimeout(() => {
      this.successMessage = '';
      this.errorMessage = '';
      this.infoMessage = '';
    }, 3000);
  }
}
