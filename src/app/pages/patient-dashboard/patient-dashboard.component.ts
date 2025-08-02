import { Component, Inject, OnInit, PLATFORM_ID } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Router } from '@angular/router';
import { isPlatformBrowser, CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-patient-dashboard',
  templateUrl: './patient-dashboard.component.html',
  styleUrls: ['./patient-dashboard.component.css'],
  imports: [CommonModule, FormsModule, RouterModule],
  standalone: true
})
export class PatientDashboardComponent implements OnInit {
  appointments: any[] = [];
  prescriptions: any[] = [];
  name: string = '';
  errorMessage: string = '';
  successMessage: string = '';
  mostVisitedDoctor: string = '';
  nextAppointment: any = null;
  medicalHistory: any[] = [];

  constructor(
    private http: HttpClient,
    private router: Router,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {}

  ngOnInit(): void {
    if (isPlatformBrowser(this.platformId)) {
      const token = localStorage.getItem('token');
      if (!token) {
        alert('Unauthorized access. Redirecting to login.');
        this.router.navigate(['/login']);
        return;
      }

      this.loadUserName(token);
      this.loadAppointments(token);
      this.loadPrescriptions(token);
      this.loadMedicalHistory(token);
    }
  }

  loadUserName(token: string): void {
    const headers = new HttpHeaders().set('Authorization', `Bearer ${token}`);
    this.http.get<any>('http://127.0.0.1:5000/user/details', { headers }).subscribe({
      next: (res) => this.name = res.name || 'Patient',
      error: (err) => {
        console.error('Failed to fetch user name:', err);
        this.errorMessage = 'Failed to load name.';
      }
    });
  }

  loadAppointments(token: string): void {
    this.http.get<{ message: string; appointments: any[] }>('http://127.0.0.1:5000/appointments/my-appointments', {
      headers: { Authorization: `Bearer ${token}` }
    }).subscribe({
      next: (res) => {
        this.appointments = res.appointments || [];
        console.log("Fetched appointments:", this.appointments);
        this.computeMostVisitedDoctor();
        this.setNextUpcomingAppointment();
      },
      error: (err) => {
        console.error('Failed to fetch appointments:', err);
        this.errorMessage = 'Error loading appointments.';
      }
    });
  }
  loadMedicalHistory(token: string): void {
  this.http.get<any[]>('http://127.0.0.1:5000/medical-history/my', {
    headers: { Authorization: `Bearer ${token}` }
  }).subscribe({
    next: (res) => {
      this.medicalHistory = res || [];
    },
    error: () => {
      this.errorMessage = 'Error loading medical history.';
    }
  });
}
  computeMostVisitedDoctor(): void {
    if (this.appointments.length === 0) {
      this.mostVisitedDoctor = '';
      return;
    }
  
    const frequencyMap: { [doctor: string]: number } = {};
  
    for (const appt of this.appointments) {
      const name = appt.doctor_name || 'Unknown';
      frequencyMap[name] = (frequencyMap[name] || 0) + 1;
    }
  
    let topDoctor = '';
    let maxCount = 0;
  
    for (const doctor in frequencyMap) {
      if (frequencyMap[doctor] > maxCount) {
        maxCount = frequencyMap[doctor];
        topDoctor = doctor;
      }
    }
  
    this.mostVisitedDoctor = topDoctor;
  }  
  setNextUpcomingAppointment(): void {
    const now = new Date();
  
    const upcoming = this.appointments
      .map(appt => {
        const datePart = appt.date; // "2025-05-13"
        const [hours, minutes] = appt.start_time.split(':'); // "21:40:00" → ["21", "40"]
  
        const apptDateTime = new Date(datePart);
        apptDateTime.setHours(+hours);
        apptDateTime.setMinutes(+minutes);
        apptDateTime.setSeconds(0);
  
        console.log(`Parsed datetime:`, apptDateTime);
  
        return { ...appt, apptDateTime };
      })
      .filter(appt => appt.apptDateTime >= now)
      .sort((a, b) => a.apptDateTime.getTime() - b.apptDateTime.getTime());
  
    this.nextAppointment = upcoming.length > 0 ? upcoming[0] : null;
  
    console.log("Next upcoming:", this.nextAppointment);
  }       
  loadPrescriptions(token: string): void {
    this.http.get<any[]>('http://127.0.0.1:5000/prescriptions/my', {
      headers: { Authorization: `Bearer ${token}` }
    }).subscribe({
      next: (res) => {
        this.prescriptions = res || [];
      },
      error: (err) => {
        console.error('Failed to fetch prescriptions:', err);
        this.errorMessage = 'Error loading prescriptions.';
      }
    });
  }

  isPast(date: string, startTime: string): boolean {
    const appointmentDateTime = new Date(`${date}T${startTime}`);
    const now = new Date();
    return appointmentDateTime < now;
  }
  shouldShowCancel(appt: any): boolean {
    return appt.status !== 'completed' && !this.isPast(appt.date, appt.start_time);
  }
  
     
  cancelAppointment(bookingId: number): void {
    const token = localStorage.getItem('token');
    if (!token) {
      alert('Please login to cancel an appointment.');
      return;
    }

    const headers = new HttpHeaders().set('Authorization', `Bearer ${token}`);
    this.http.delete(`http://127.0.0.1:5000/appointments/cancel/${bookingId}`, { headers }).subscribe({
      next: (res: any) => {
        this.successMessage = res.message || 'Appointment cancelled successfully.';
        this.loadAppointments(token);
      },
      error: (err) => {
        console.error('Cancellation failed:', err);
        this.errorMessage = err.error?.error || 'Failed to cancel appointment.';
      }
    });
  }

  logout(): void {
    if (isPlatformBrowser(this.platformId)) {
      localStorage.clear();
      this.router.navigate(['/']);
    }
  }
}
