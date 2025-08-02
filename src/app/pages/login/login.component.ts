import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpClientModule, HttpHeaders } from '@angular/common/http';
import { Router, RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { TranslateService } from '@ngx-translate/core';
import { TranslateModule } from '@ngx-translate/core';
import {Inject,PLATFORM_ID} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

@Component({
  selector: 'app-login',
  standalone: true,
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css'],
  imports: [CommonModule, FormsModule, HttpClientModule, RouterModule,TranslateModule]
})
export class LoginComponent {
  email: string = '';
  password: string = '';
  showPassword: boolean = false;
  errorMessage: string = '';
  isBrowser: boolean;


constructor(
  @Inject(PLATFORM_ID) private platformId: Object,
  private http: HttpClient,
  private router: Router,
  private translate: TranslateService
) {
  this.isBrowser = isPlatformBrowser(this.platformId);

  if (this.isBrowser) {
    const supportedLangs = ['en', 'hin', 'fr', 'de', 'pl'];
    const savedLang = localStorage.getItem('selectedLang') || 'en';

    this.translate.addLangs(supportedLangs);
    this.translate.setDefaultLang('en');
    this.translate.use(savedLang);
  }
}

  togglePassword() {
    this.showPassword = !this.showPassword;
  }

  onLogin() {
    if (!this.email || !this.password) {
      this.showError(this.translate.instant('login.error.missingFields'));
      return;
    }

    this.http.post('http://127.0.0.1:5000/auth/login', {
      email: this.email,
      password: this.password
    }).subscribe({
      next: (response: any) => {
        if (response.token && response.role) {
          localStorage.setItem('token', response.token);
          localStorage.setItem('role', response.role);
          alert(this.translate.instant('login.success'));

          if (response.role === 'admin') {
            this.router.navigate(['/admin-dashboard']);
          } else if (response.role === 'doctor') {
            this.router.navigate(['/doctor-dashboard']);
          } else if (response.role === 'pharmacist') {
            this.router.navigate(['/pharmacist-dashboard']);
          } else {
            const headers = new HttpHeaders().set('Authorization', `Bearer ${response.token}`);
            this.http.get<any>('http://127.0.0.1:5000/user/patient-profile-status', { headers }).subscribe({
              next: (status) => {
                if (status.profile_complete) {
                  this.router.navigate(['/patient-dashboard']);
                } else {
                  this.router.navigate(['/update-profile']);
                }
              },
              error: (err) => {
                console.error('Status check failed', err);
                this.showError(this.translate.instant('login.error.statusCheck'));
              }
            });
          }
        } else {
          this.showError(this.translate.instant('login.error.noToken'));
        }
      },
      error: (error) => {
        console.error('Login error:', error);
        this.showError(this.translate.instant('login.error.invalidCredentials'));
      }
    });
  }

  showError(message: string) {
    this.errorMessage = message;
    setTimeout(() => this.errorMessage = '', 3000);
  }
}
