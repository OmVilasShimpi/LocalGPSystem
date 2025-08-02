import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import { TranslateService } from '@ngx-translate/core';
import { TranslateModule } from '@ngx-translate/core';
import { Inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';


@Component({
  selector: 'app-set-password',
  standalone: true,
  imports: [CommonModule, FormsModule, HttpClientModule, RouterModule,TranslateModule],
  templateUrl: './set-password.component.html',
  styleUrls: ['./set-password.component.css']
})
export class SetPasswordComponent implements OnInit {
  password: string = '';
  confirmPassword: string = '';
  token: string = '';
  errorMessage: string = '';
  successMessage: string = '';
  showPassword: boolean = false;

  constructor(
  private http: HttpClient,
  private route: ActivatedRoute,
  private router: Router,
  private translate: TranslateService,
  @Inject(PLATFORM_ID) private platformId: Object
) {
  if (isPlatformBrowser(this.platformId)) {
    const supportedLangs = ['en', 'hin', 'fr', 'de', 'pl'];
    const lang = localStorage.getItem('selectedLang') || 'en';

    this.translate.addLangs(supportedLangs);
    this.translate.setDefaultLang('en');
    this.translate.use(lang);
  }
}
  ngOnInit() {
    this.route.queryParams.subscribe(params => {
      this.token = params['token'];
      console.log('Token received:', this.token);
    });
  }

  togglePasswordVisibility() {
    this.showPassword = !this.showPassword;
  }

  onSetPassword() {
    if (this.password !== this.confirmPassword) {
      this.errorMessage = this.translate.instant('set.error.mismatch');
      this.successMessage = '';
      return;
    }

    if (!this.token) {
      this.errorMessage = this.translate.instant('set.error.token');
      this.successMessage = '';
      return;
    }

    const payload = {
      token: this.token,
      new_password: this.password
    };

    this.http.post('http://127.0.0.1:5000/user/set-password', payload).subscribe(
      () => {
        this.successMessage = this.translate.instant('set.success');
        this.errorMessage = '';
        setTimeout(() => {
          this.router.navigate(['/login']);
        }, 2500);
      },
      (error) => {
        console.error('Set password error:', error);
        this.errorMessage =
          error.error?.error
            ? this.translate.instant(`set.error.${error.error.error}`)
            : this.translate.instant('set.error.expired');
        this.successMessage = '';
      }
    );
  }
}
