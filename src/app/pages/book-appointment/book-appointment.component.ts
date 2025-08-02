import { Component, OnInit } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router'; 
import { CommonModule } from '@angular/common';
import { isPlatformBrowser } from '@angular/common';
import { Inject, PLATFORM_ID } from '@angular/core';
import { Router } from '@angular/router';

@Component({
  selector: 'app-book-appointment',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './book-appointment.component.html',
  styleUrls: ['./book-appointment.component.css']
})
export class BookAppointmentComponent implements OnInit {
  doctors: any[] = [];
  filteredDoctors: any[] = [];
  searchAddress: string = '';
  selectedDoctorId: string = '';
  selectedDate: string = '';
  minDate: string = new Date().toISOString().split('T')[0]; 
  availableSlots: any[] = [];
  message: string | null = null;
  error: string | null = null;
  isLoadingSlots: boolean = false;
  preferredStartTime: string = '';
  preferredEndTime: string = '';
  originalSlots: any[] = [];
  constructor(
    private http: HttpClient,
    private router: Router,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {}
  ngOnInit(): void {
    this.fetchAllDoctors();
  }
  getToken(): string | null {
    if (isPlatformBrowser(this.platformId)) {
      return localStorage.getItem('token');
    }
    return null;
  }
  fetchAllDoctors(): void {
    const token = this.getToken();
    if (!token) return;

    this.http.get<any[]>('http://127.0.0.1:5000/user/get-all-doctors-dropdown', {
      headers: { Authorization: `Bearer ${token}` }
    }).subscribe({
      next: (res) => {
        this.doctors = res;
        this.filteredDoctors = res;
      },
      error: (err) => {
        console.error('Failed to fetch doctors:', err);
        this.error = 'error_loading_doctors';
      }
    });
  }
  searchDoctorsByAddress(): void {
  const token = this.getToken();
  if (!token) {
    this.error = ' Unauthorized access. Please log in.';
    return;
  }

  const trimmed = this.searchAddress.trim().toUpperCase();
  if (!trimmed) {
    this.error = 'Please enter a valid postcode or address.';
    return;
  }

  // Reset state before request
  this.filteredDoctors = [];
  this.selectedDoctorId = '';
  this.availableSlots = [];
  this.error = '';
  this.message = '';

  const encodedPostcode = encodeURIComponent(trimmed);

  this.http.get<any>(`http://127.0.0.1:5000/user/search-doctors?postcode_prefix=${encodedPostcode}`, {
    headers: { Authorization: `Bearer ${token}` }
  }).subscribe({
    next: (res) => {
      this.filteredDoctors = res.doctors || [];

      if (res.fallback) {
        const fallbackList = res.checked_prefixes?.join(', ') || 'nearby areas';
        this.error = ` No doctors found for ${res.searched_postcode}. Showing all available doctors instead. (Checked: ${fallbackList})`;
      } else if (this.filteredDoctors.length === 0) {
        this.error = ` No doctors found for ${trimmed} or nearby.`;
      } else {
        this.error = '';
      }
    },
    error: (err) => {
      console.error(' Doctor fetch failed:', err);
      if (err.error?.error === 'invalid_postcode') {
        this.error = ' Invalid postcode entered. Please try again with a valid UK postcode.';
      } else {
        this.error = ' An unexpected error occurred while fetching doctors.';
      }
    }
  });
}
  clearTimeFilters(): void {
    this.preferredStartTime = '';
    this.preferredEndTime = '';
    this.filterSlotsByTime();
  }  
  onDoctorOrDateChange(): void {
    this.availableSlots = [];  // Clear old slots immediately
    this.error = null;
  
    if (this.selectedDoctorId && this.selectedDate) {
      // Force date to refresh binding (optional but safe)
      this.selectedDate = this.selectedDate + '';
      
      // Slight delay to ensure DOM rebinds (helps if using cached values)
      setTimeout(() => {
        this.loadAvailableSlots();
      });
    } else {
      this.message = null; // No valid doctor/date, remove old message
    }
  }  
  loadAvailableSlots(): void {
    this.error = null;
    this.isLoadingSlots = true;
    this.availableSlots = [];
  
    if (!this.selectedDoctorId || !this.selectedDate) {
      this.error = 'Please select both a doctor and a date.';
      this.isLoadingSlots = false;
      return;
    }
  
    const isoDate = new Date(this.selectedDate).toISOString().split('T')[0];
    const url = `http://127.0.0.1:5000/appointments/available-slots/${this.selectedDoctorId}?date=${isoDate}`;
    console.log("Request URL:", url);
  
    this.http.get<{ slots: any[] }>(url).subscribe({
      next: (res) => {
        this.isLoadingSlots = false;
        if (Array.isArray(res.slots) && res.slots.length > 0) {
          const now = new Date();
          let nextFound = false;
  
          // Filter out only future slots based on actual slot time
          const futureSlots = res.slots.filter(slot => {
            const slotDateTime = new Date(`${slot.date}T${slot.start_time}`);
            const isFuture = slotDateTime > now;
  
            if (isFuture && !nextFound) {
              slot.isNext = true;
              nextFound = true;
            } else {
              slot.isNext = false;
            }
  
            return isFuture;
          });
  
          this.originalSlots = futureSlots;
          this.availableSlots = [...futureSlots];
  
          this.filterSlotsByTime();
  
          if (this.availableSlots.length === 0) {
            this.message = ' All earlier slots for today have passed.';
          } else {
            this.message = null;
          }
        } else {
          this.availableSlots = [];
          this.message = ' No slots available for the selected doctor and date.';
        }
      },
      error: (err) => {
        this.isLoadingSlots = false;
        this.availableSlots = [];
        this.error = err.error?.error || ' Failed to fetch available slots. Please try again.';
        this.message = null;
      }
    });
  }        
  filterSlotsByTime(): void {
    if (!this.preferredStartTime && !this.preferredEndTime) {
      // No filters: restore all valid future slots
      this.availableSlots = [...this.originalSlots];
      return;
    }
  
    const start = this.preferredStartTime;
    const end = this.preferredEndTime;
  
    // Always filter from originalSlots to ensure consistent results
    this.availableSlots = this.originalSlots.filter(slot => {
      return (!start || slot.start_time >= start) &&
             (!end || slot.end_time <= end);
    });
  }
  
  getDoctorName(doctorId: number): string {
    const doc = this.filteredDoctors.find(d => d.id === doctorId);
    return doc ? doc.name : 'Doctor';
  }
  formatToAmPm(time: string): string {
    const [hourStr, minuteStr] = time.split(':');
    let hour = parseInt(hourStr, 10);
    const minute = minuteStr.padStart(2, '0');
    const suffix = hour >= 12 ? 'PM' : 'AM';
    hour = hour % 12 || 12;
    return `${hour}:${minute} ${suffix}`;
  }    
  bookAppointment(slot: { doctor_id: number, date: string, start_time: string, end_time: string }): void {
    const token = this.getToken();
    if (!token) {
      alert('Please login to book an appointment.');
      return;
    }
  
    this.http.post('http://127.0.0.1:5000/appointments/book-slot', {
      doctor_id: slot.doctor_id,
      date: slot.date,
      start_time: slot.start_time,
      end_time: slot.end_time
    }, {
      headers: { Authorization: `Bearer ${token}` }
    }).subscribe({
      next: () => {
        const doctor = this.filteredDoctors.find(doc => doc.id === slot.doctor_id);
        const doctorName = doctor ? doctor.name : 'your doctor';
        const address = doctor ? doctor.clinic_address : 'the clinic';
  
        this.message = ` Your appointment with ${doctorName} on ${slot.date} from ${slot.start_time} to ${slot.end_time} has been successfully booked. A confirmation email has been sent to your registered email address.`;
        this.error = null;
  
        this.availableSlots = []; // Clear slots from view
  
        setTimeout(() => {
          this.router.navigate(['/patient-dashboard']);
        }, 3500); // Wait before redirecting
      },
      error: (err) => {
        console.error('Booking error:', err);
        this.error = '❌ ' + (err.error?.message_key || 'Booking failed. Try again.');
        this.message = null;
  
        setTimeout(() => this.error = null, 4000);
      }
    });
  }  
}  
