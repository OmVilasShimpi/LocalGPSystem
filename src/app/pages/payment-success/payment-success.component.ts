import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { TranslateModule } from '@ngx-translate/core';
@Component({
  selector: 'app-payment-success',
  imports:[TranslateModule], 
  templateUrl: './payment-success.component.html',
  styleUrls: ['./payment-success.component.css']
})
export class PaymentSuccessComponent {

  constructor(private router: Router, public translate: TranslateService) {
  const supportedLangs = ['en', 'hin', 'fr', 'de', 'pl'];
  const savedLang = localStorage.getItem('selectedLang') || 'en';

  this.translate.addLangs(supportedLangs);
  this.translate.setDefaultLang('en');
  this.translate.use(savedLang);
}


  goToDashboard(): void {
    const role = localStorage.getItem('role');
    if (role === 'admin') {
      this.router.navigate(['/admin-dashboard']);
    } else if (role === 'doctor') {
      this.router.navigate(['/doctor-dashboard']);
    } else if (role === 'patient') {
      this.router.navigate(['/patient-dashboard']);
    } else if (role === 'pharmacist') {
      this.router.navigate(['/pharmacist-dashboard']);
    } else {
      this.router.navigate(['/home']);
    }
  }
}
