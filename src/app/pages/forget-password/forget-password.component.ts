import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { RouterModule, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import { TranslateService } from '@ngx-translate/core';
import { TranslateModule } from '@ngx-translate/core';
import {Inject,PLATFORM_ID} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

@Component({
  selector: 'app-forget-password',
  standalone: true,
  imports: [CommonModule, FormsModule, HttpClientModule, RouterModule,TranslateModule],
  templateUrl: './forget-password.component.html',
  styleUrls: ['./forget-password.component.css']
})
export class ForgetPasswordComponent {
  email: string = '';
  errorMessage: string = '';
  successMessage: string = '';
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
  onRequestReset() {
    if (!this.email) {
      this.errorMessage = this.translate.instant('forgot.error.missingEmail');
      this.successMessage = '';
      return;
    }

    this.http.post<any>('http://127.0.0.1:5000/user/generate-reset-token', { email: this.email }).subscribe(
      () => {
        this.successMessage = this.translate.instant('forgot.success.sent');
        this.errorMessage = '';
        this.email = '';

        setTimeout(() => {
          this.router.navigate(['/login']);
        }, 3000);
      },
      (error) => {
        console.error(error);
        this.errorMessage = error.error?.error
          ? this.translate.instant(`forgot.error.${error.error.error}`)
          : this.translate.instant('forgot.error.generic');
        this.successMessage = '';
      }
    );
  }
}
