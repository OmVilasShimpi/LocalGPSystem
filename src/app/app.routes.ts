import { Routes } from '@angular/router';
import { LoginComponent } from './pages/login/login.component';
import { SignupComponent } from './pages/signup/signup.component';
import { AdminDashboardComponent } from './pages/admin-dashboard/admin-dashboard.component';
import { DoctorDashboardComponent } from './pages/doctor-dashboard/doctor-dashboard.component';
import { PatientDashboardComponent } from './pages/patient-dashboard/patient-dashboard.component';
import { PharmacistDashboardComponent } from './pages/pharmacist-dashboard/pharmacist-dashboard.component';
import { HomeComponent } from './pages/home/home.component';
import { SetPasswordComponent } from './pages/set-password/set-password.component';
import { ResetPasswordComponent } from './pages/reset-password/reset-password.component';
import { ForgetPasswordComponent } from './pages/forget-password/forget-password.component';
import { BookAppointmentComponent } from './pages/book-appointment/book-appointment.component';
import { UpdateProfileComponent } from './pages/update-profile/update-profile.component';
import { PaymentSuccessComponent } from './pages/payment-success/payment-success.component';
import { PaymentCancelComponent } from './pages/payment-cancel/payment-cancel.component';
export const routes: Routes = [
  { path: '', redirectTo: 'home', pathMatch: 'full' },
  { path: 'home', component: HomeComponent },
  { path: 'login', component: LoginComponent },
  { path: 'update-profile', component: UpdateProfileComponent },
  { path: 'signup', component: SignupComponent },
  { path: 'set-password', component: SetPasswordComponent },
  { path: 'reset-password', component: ResetPasswordComponent },
  { path: 'forget-password', component: ForgetPasswordComponent },

  // Role-based dashboards
  { path: 'admin-dashboard', component: AdminDashboardComponent },
  { path: 'doctor-dashboard', component: DoctorDashboardComponent },
  { path: 'patient-dashboard', component: PatientDashboardComponent },
  { path: 'pharmacist-dashboard', component: PharmacistDashboardComponent },

  // New route for booking appointments
  { path: 'book-appointment', component: BookAppointmentComponent },
  { path: 'pay-success/:prescriptionId', component: PaymentSuccessComponent },
  { path: 'pay-cancel/:prescriptionId', component: PaymentCancelComponent },


  // Fallback
  { path: '**', redirectTo: 'home' }
];
