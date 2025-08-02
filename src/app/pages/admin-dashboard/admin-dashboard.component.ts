import { Component, Inject, OnInit, PLATFORM_ID } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { trigger, transition, style, animate } from '@angular/animations';

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, MatSnackBarModule],
  templateUrl: './admin-dashboard.component.html',
  styleUrls: ['./admin-dashboard.component.css'],
  animations: [
    trigger('fadeIn', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateY(10px)' }),
        animate('300ms ease-in', style({ opacity: 1, transform: 'translateY(0)' }))
      ])
    ])
  ]
})
export class AdminDashboardComponent implements OnInit {
  newDoctor = { name: '', email: '' };
  newPharmacist = { name: '', email: '' };

  doctors: any[] = [];
  pharmacists: any[] = [];
  patients: any[] = [];

  constructor(
    private http: HttpClient,
    private snackBar: MatSnackBar,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {}

  ngOnInit(): void {
    this.loadDoctors();
    this.loadPharmacists();
    this.loadPatients();
  }

  getAuthHeaders() {
    if (isPlatformBrowser(this.platformId)) {
      const token = localStorage.getItem('token');
      return {
        headers: {
          Authorization: token || ''
        }
      };
    }
    return {};
  }

  showSuccess(message: string) {
    this.snackBar.open(message, 'Close', {
      duration: 3000,
      panelClass: ['snackbar-success']
    });
  }

  showError(message: string) {
    this.snackBar.open(message, 'Close', {
      duration: 4000,
      panelClass: ['snackbar-error']
    });
  }

  addUser(role: 'doctor' | 'pharmacist') {
    const data = role === 'doctor' ? this.newDoctor : this.newPharmacist;

    if (!data.name || !data.email) {
      this.showError('Please fill in all fields.');
      return;
    }

    this.http.post(`http://127.0.0.1:5000/user/add-user`, {
      name: data.name,
      email: data.email,
      role
    }, this.getAuthHeaders()).subscribe({
      next: () => {
        this.showSuccess(`${role.charAt(0).toUpperCase() + role.slice(1)} added successfully.`);
        if (role === 'doctor') {
          this.newDoctor = { name: '', email: '' };
          this.loadDoctors();
        } else {
          this.newPharmacist = { name: '', email: '' };
          this.loadPharmacists();
        }
      },
      error: (err) => {
        console.error(err);
        this.showError(err?.error?.error || 'Error adding user.');
      }
    });
  }

  deleteUser(userId: number) {
    const confirmed = confirm('Are you sure you want to delete this user?');
    if (!confirmed) return;

    this.http.delete(`http://127.0.0.1:5000/user/delete/${userId}`, this.getAuthHeaders()).subscribe({
      next: () => {
        this.showSuccess('User deleted successfully.');
        this.loadDoctors();
        this.loadPharmacists();
      },
      error: (err) => {
        console.error(err);
        this.showError('Failed to delete user.');
      }
    });
  }

  loadDoctors() {
    this.http.get<any[]>('http://127.0.0.1:5000/user/get-all-doctors', this.getAuthHeaders()).subscribe(
      (res) => (this.doctors = res),
      (err) => this.showError('Error loading doctors')
    );
  }

  loadPharmacists() {
    this.http.get<any[]>('http://127.0.0.1:5000/user/get-all-pharmacists', this.getAuthHeaders()).subscribe(
      (res) => (this.pharmacists = res),
      (err) => this.showError('Error loading pharmacists')
    );
  }

  loadPatients() {
    this.http.get<any[]>('http://127.0.0.1:5000/user/get-all-patients', this.getAuthHeaders()).subscribe(
      (res) => (this.patients = res),
      (err) => this.showError('Error loading patients')
    );
  }

  logout() {
    if (isPlatformBrowser(this.platformId)) {
      localStorage.removeItem('token');
      this.showSuccess('Logged out successfully');
      setTimeout(() => window.location.href = '/', 1500);
    }
  }
}
