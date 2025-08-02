import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-pharmacist-dashboard',
  templateUrl: './pharmacist-dashboard.component.html',
  styleUrls: ['./pharmacist-dashboard.component.css'],
  standalone: true,
  imports: [FormsModule, CommonModule]
})
export class PharmacistDashboardComponent implements OnInit {
  pharmacistData: any = {};
  updatedData = { license_number: '', store_name: '', store_address: '', store_postcode:'' };

  prescriptions: any[] = [];
  allPrescriptions: any[] = [];
  selectedPrescriptionId: number | null = null;
  paymentNote: string = '';

  selectedPatientId: number | null = null;
  selectedPatientName: string = '';
  patientPrescriptions: any[] = [];

  successMessage = '';
  errorMessage = '';

  isProfileComplete: boolean = false;
  showProfileForm: boolean = false;
  inventory: { medicine_name: string, quantity: number }[] = [];

  dispensedCount: number = 0;
  sortOption = 'default';

  constructor(private http: HttpClient, private router: Router) {}

  ngOnInit() {
    const token = this.getToken();
    if (!token) {
      this.router.navigate(['/login']);
      return;
    }
    this.loadPharmacistProfile();
    this.loadPrescriptions();
    this.loadInventory();
    this.loadPharmacistData();
  }

  getToken(): string | null {
    return typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  }

  getAuthHeaders() {
    return { headers: { Authorization: `Bearer ${this.getToken()}` } };
  }

  loadPharmacistProfile() {
    this.http.get('http://127.0.0.1:5000/user/details', this.getAuthHeaders())
      .subscribe((res: any) => {
        this.pharmacistData = res;
        this.updatedData = {
          license_number: res.license_number || '',
          store_name: res.store_name || '',
          store_address: res.store_address || '',
          store_postcode: res.store_postcode || ''
        };
        this.isProfileComplete = !!(this.updatedData.license_number && this.updatedData.store_name && this.updatedData.store_address);
        this.showProfileForm = !this.isProfileComplete;
      });
  }
  loadPharmacistData(): void {
    const token = localStorage.getItem('token');
    if (!token) {
      this.errorMessage = 'Unauthorized access';
      return;
    }
    this.http.get<any>('http://127.0.0.1:5000/prescriptions/pharmacist/dashboard', this.getAuthHeaders()).subscribe({
      next: (res) => {
        this.prescriptions = res.prescriptions || [];
        this.inventory = res.inventory || [];
  
        // Count dispensed prescriptions (adjust if statuses differ)
        this.dispensedCount = this.prescriptions.filter(p =>
          ['dispensed', 'Paid', 'collected'].includes(p.status?.toLowerCase())
        ).length;
  
        this.successMessage = 'Dashboard data loaded';
      },
      error: (err) => {
        console.error('Error loading pharmacist data:', err);
        this.errorMessage = 'Failed to load pharmacist data';
      }
    });
  }
  
  updateProfile() {
    this.http.post('http://127.0.0.1:5000/user/update-pharmacist-profile', this.updatedData, this.getAuthHeaders())
      .subscribe({
        next: () => {
          this.showSuccess(' Profile updated!');
          this.loadPharmacistProfile();
          this.showProfileForm = false;
        },
        error: () => this.showError(' Update failed.')
      });
  }
  sortInventory(): void {
    if (this.sortOption === 'asc') {
      this.inventory.sort((a, b) => a.quantity - b.quantity);
    } else if (this.sortOption === 'desc') {
      this.inventory.sort((a, b) => b.quantity - a.quantity);
    } else {
      this.loadInventory(); // Reset to default order from server
    }
  }
  loadPrescriptions() {
    this.http.get<any>('http://127.0.0.1:5000/prescriptions/pharmacy', this.getAuthHeaders())
      .subscribe({
        next: (res) => {
          this.allPrescriptions = res;
          this.prescriptions = res.filter((p: any) => p.status !== 'collected');
        },
        error: () => this.showError(' Failed to load prescriptions.')
      });
  }

  selectPatient(patientId: number): void {
    console.log('Clicked patient ID:', patientId);
    this.selectedPatientId = patientId;
    this.patientPrescriptions = this.allPrescriptions.filter(p => p.patient_id === patientId);
    this.selectedPatientName = this.patientPrescriptions[0]?.patient_name || 'Patient';
  }
  

  closePatientView(): void {
    this.selectedPatientId = null;
    this.patientPrescriptions = [];
  }

  selectPrescription(prescription: any) {
    this.selectedPrescriptionId = prescription.id;
    if (prescription.payment_note) {
      this.paymentNote = prescription.payment_note;
    }
  }
  

  updatePrescriptionStatus() {
    if (!this.selectedPrescriptionId) return;
  
    console.log("🧾 Submitting payment note:", this.paymentNote);  //  Should log actual value
  
    const headers = {
      'Authorization': `Bearer ${this.getToken()}`,
      'Content-Type': 'application/json' //  Required so Flask parses body correctly
    };
  
    this.http.put(
      `http://127.0.0.1:5000/prescriptions/status/${this.selectedPrescriptionId}`,
      {
        status: 'dispensed',
        payment_note: this.paymentNote
      },
      { headers } //  Wrap headers inside a config object
    ).subscribe({
      next: () => {
        this.showSuccess(' Prescription marked as dispensed.');
        this.loadPrescriptions();
        this.selectedPrescriptionId = null;
        //this.paymentNote = ''; //  Reset after use
      },
      error: () => this.showError(' Failed to update prescription.')
    });
  }
  

  markAsPaid(prescriptionId: number) {
    const headers = this.getAuthHeaders();
    this.http.put(`http://127.0.0.1:5000/prescriptions/status/${prescriptionId}`, {
      status: 'Paid',
      payment_note: this.paymentNote || ''
    }, headers).subscribe({
      next: () => {
        this.successMessage = ' Prescription marked as Paid!';
        this.loadPrescriptions();
      },
      error: () => this.errorMessage = ' Failed to mark as Paid.'
    });
  }
  
  markAsCollected(prescriptionId: number) {
    const headers = this.getAuthHeaders();
    this.http.put(`http://127.0.0.1:5000/prescriptions/status/${prescriptionId}`, {
      status: 'collected',
      payment_note: this.paymentNote || ''
    }, headers).subscribe({
      next: () => {
        this.successMessage = ' Prescription marked as Collected!';
        this.loadPrescriptions();
      },
      error: () => this.errorMessage = ' Failed to mark as Collected.'
    });
  }
  
  loadInventory() {
    this.http.get<any>('http://127.0.0.1:5000/prescriptions/pharmacy/inventory', this.getAuthHeaders())
      .subscribe({
        next: (res) => {
          this.inventory = res.inventory;
        },
        error: () => this.showError(' Failed to load inventory.')
      });
  }
  

  logout() {
    const confirmed = confirm('Are you sure you want to logout?');
    if (confirmed) {
      localStorage.clear();
      this.router.navigate(['/login']);
    }
  }

  private showSuccess(msg: string) { this.successMessage = msg; this.clearMessages(); }
  private showError(msg: string) { this.errorMessage = msg; this.clearMessages(); }

  private clearMessages() {
    setTimeout(() => {
      this.successMessage = '';
      this.errorMessage = '';
    }, 3000);
  }
}
