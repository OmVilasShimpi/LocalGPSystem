declare global {
  interface Window {
    voiceflow: any;
  }
}
import { Component, AfterViewInit, Inject, PLATFORM_ID, HostListener, OnInit, OnDestroy } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule, TranslateModule],
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.css']
})
export class HomeComponent implements AfterViewInit, OnInit,OnDestroy {
  doctors = [
    { name: 'Dr. Sarah Patel', speciality: 'Cardiologist', image: 'https://randomuser.me/api/portraits/women/44.jpg' },
    { name: 'Dr. John Smith', speciality: 'Dermatologist', image: 'https://randomuser.me/api/portraits/men/32.jpg' },
    { name: 'Dr. Emily Brown', speciality: 'Neurologist', image: 'https://randomuser.me/api/portraits/women/65.jpg' },
    { name: 'Dr. Alex Johnson', speciality: 'Orthopedic', image: 'https://randomuser.me/api/portraits/men/47.jpg' },
  ];

  contact = { name: '', email: '', message: '' };
  isNavbarVisible = true;
  lastScrollPosition = 0;
  isBrowser: boolean;

  constructor(
  @Inject(PLATFORM_ID) private platformId: Object,
  private translate: TranslateService,
  private http: HttpClient
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
  ngOnInit(): void {
    if (this.isBrowser && !document.getElementById('vf-script')) {
      const script = document.createElement('script');
      script.type = 'text/javascript';
      script.src = 'https://cdn.voiceflow.com/widget-next/bundle.mjs';
      script.setAttribute('id', 'vf-script');
  
      script.onload = () => {
        window.voiceflow.chat.load({
          verify: { projectID: '681cb474842b81606b0581de' },
          url: 'https://general-runtime.voiceflow.com',
          versionID: 'production',
          voice: {
            url: "https://runtime-api.voiceflow.com"
          }
        });
      };
  
      const s = document.getElementsByTagName('script')[0];
      if (s && s.parentNode) {
        s.parentNode.insertBefore(script, s);
      } else {
        document.body.appendChild(script);
      }
    }
  }  
  ngAfterViewInit(): void {
    if (this.isBrowser) {
      setTimeout(() => {
        this.animateCounter('doctor-count', 80);
        this.animateCounter('patient-count', 1200);
        this.animateCounter('appointment-count', 600);
      }, 500); // Ensures DOM is ready
    }
  }  
  ngOnDestroy(): void {
    if (this.isBrowser) {
      const script = document.getElementById('vf-script');
      if (script) script.remove();
  
      const widget = document.getElementById('vf-widget');
      if (widget) widget.remove();
  
      const style = document.querySelector('style[data-vf]');
      if (style) style.remove();
    }
  }  
  animateCounter(id: string, target: number): void {
    const element = this.isBrowser ? document.getElementById(id) : null;
    if (!element) return;
    let count = 0;
    const increment = Math.ceil(target / 200);

    const updateCount = () => {
      count += increment;
      if (count < target) {
        element.textContent = `${count}`;
        requestAnimationFrame(updateCount);
      } else {
        element.textContent = `${target}`;
      }
    };

    requestAnimationFrame(updateCount);
  }

  switchLanguageString(lang: string): void {
    if (!this.isBrowser) return;
    this.translate.use(lang);
    localStorage.setItem('selectedLang', lang);
  }
  isDropdownOpen = false;

  toggleLanguageDropdown(): void {
    this.isDropdownOpen = !this.isDropdownOpen;
  }
  submitContactForm(): void {
    if (this.contact.name && this.contact.email && this.contact.message) {
      this.http.post('http://localhost:5000/contact', this.contact).subscribe({
        next: () => {
          const thankYou = this.translate.instant('home.contact.alert.success', {
            name: this.contact.name
          });
          alert(` ${thankYou}`);
          this.contact = { name: '', email: '', message: '' };
        },
        error: () => {
          alert(' Failed to send message. Please try again later.');
        }
      });
    } else {
      alert(this.translate.instant('home.contact.alert.error'));
    }
  }
  

  @HostListener('window:scroll', [])
  onWindowScroll(): void {
    const currentScroll = this.isBrowser
      ? window.pageYOffset || document.documentElement.scrollTop
      : 0;

    if (currentScroll > this.lastScrollPosition && currentScroll > 100) {
      this.isNavbarVisible = false;
    } else {
      this.isNavbarVisible = true;
    }

    this.lastScrollPosition = currentScroll;
  }
}
