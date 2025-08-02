import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute } from '@angular/router';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import { TranslateService } from '@ngx-translate/core';
import { TranslateModule } from '@ngx-translate/core';
import {Inject,PLATFORM_ID} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [CommonModule, FormsModule, HttpClientModule, RouterModule,TranslateModule],
  templateUrl: './reset-password.component.html',
  styleUrls: ['./reset-password.component.css']
})
export class ResetPasswordComponent implements OnInit {
  newPassword: string = '';
  confirmPassword: string = '';
  errorMessage: string = '';
  successMessage: string = '';
  showPassword: boolean = false;
  token: string = '';
  isBrowser: boolean;

  constructor(
  @Inject(PLATFORM_ID) private platformId: Object,
  private http: HttpClient,
  private route: ActivatedRoute,
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
  ngOnInit() {
    this.route.queryParams.subscribe(params => {
      this.token = params['token'];
      console.log('Token:', this.token);
    });
  }

  togglePassword() {
    this.showPassword = !this.showPassword;
  }

  onResetPassword() {
    if (this.newPassword !== this.confirmPassword) {
      this.errorMessage = this.translate.instant('reset.error.mismatch');
      this.successMessage = '';
      return;
    }

    const resetData = {
      token: this.token,
      new_password: this.newPassword
    };

    this.http.post('http://127.0.0.1:5000/user/reset-password', resetData).subscribe(
      () => {
        this.successMessage = this.translate.instant('reset.success');
        this.errorMessage = '';
        this.newPassword = '';
        this.confirmPassword = '';
      },
      () => {
        this.errorMessage = this.translate.instant('reset.error.failed');
        this.successMessage = '';
      }
    );
  }
}
