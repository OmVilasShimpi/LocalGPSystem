import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpHeaders, HttpClientModule } from '@angular/common/http';
import { Router, RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-update-profile',
  standalone: true,
  templateUrl: './update-profile.component.html',
  styleUrls: ['./update-profile.component.css'],
  imports: [CommonModule, FormsModule, HttpClientModule, RouterModule]
})
export class UpdateProfileComponent {
  step = 1;
  address = '';
  city = '';
  pincode = '';
  preferred_pharmacy_id = '';
  pharmacies: any[] = [];
  message = '';

  constructor(private http: HttpClient, private router: Router) {}

  // Step 1: Save address and then load pharmacies
  submitAddress() {
    const token = localStorage.getItem('token');
    if (!token) {
      this.message = 'Please log in again.';
      return;
    }

    const headers = new HttpHeaders().set('Authorization', `Bearer ${token}`);
    const body = { address: this.address, city: this.city, pincode: this.pincode };

    this.http.post('http://127.0.0.1:5000/user/update-patient-profile', body, { headers }).subscribe({
      next: () => {
        this.message = '';
        this.fetchAllPharmacies(headers);  //  Load pharmacies after saving address
        this.step = 2;
      },
      error: (err) => {
        console.error('Address update failed:', err);
        this.message = 'Failed to save address.';
      }
    });
  }

  // Fetch all pharmacists (no filtering now)
  fetchAllPharmacies(headers: HttpHeaders) {
    this.http.get<any[]>('http://127.0.0.1:5000/user/get-all-pharmacists-dropdown', { headers }).subscribe({
      next: (data) => {
        this.pharmacies = data;
        this.message = '';
      },
      error: (err) => {
        console.error('Pharmacy fetch failed:', err);
        this.message = 'Failed to load pharmacies.';
      }
    });
  }

  // Step 2: Save selected pharmacy
  submitPharmacy() {
    const token = localStorage.getItem('token');
    if (!token) {
      this.message = 'Please log in again.';
      return;
    }

    const headers = new HttpHeaders().set('Authorization', `Bearer ${token}`);
    const body = { preferred_pharmacy_id: this.preferred_pharmacy_id };

    this.http.post('http://127.0.0.1:5000/user/update-patient-profile', body, { headers }).subscribe({
      next: () => {
        alert('Profile updated successfully!');
        this.router.navigate(['/patient-dashboard']);
      },
      error: (err) => {
        console.error('Pharmacy update failed:', err);
        this.message = 'Failed to save preferred pharmacy.';
      }
    });
  }
}
